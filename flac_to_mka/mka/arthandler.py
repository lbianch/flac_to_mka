import atexit
import os
import shutil
import subprocess
from logging import getLogger

from PIL import Image

from flac_to_mka.flac import metadata
from flac_to_mka.util import ext, flacutil


logging = getLogger(__name__)


class InvalidArtworkFormatError(Exception):
    pass


class Artwork:
    """Class to handle the management of cover artwork.  If an image is
    specified via command line, it is the only considered artwork.
    Otherwise, the directory is checked for any ``jpg``, ``jpeg``, or ``png``
    files.  Of the found images, the highest resolution square image
    is chosen.  It requires that the width and height both be at least 500px,
    and that the ratio of width to height be within 1% of square.  If no
    such artwork is found, then the FLAC files themselves are checked for
    embedded artwork, held to the same resolution and aspect ratio standards.
    The class may end up copying images and creating new files, which are
    able to be deleted afterwards via the ``Clean`` method, which is automatically
    registered via ``atexit.register``.
    """

    def __init__(self, args, mdata, filename):
        """Params:
        ---
        args: For the command line arguments, parsed from ``tools.flac.arguments
        mdata: Only checked to see if it is a ``metadata.AlbumMetadata`` or not
        filename:  [str], The output FLAC file name.
        """
        self.owns_image = False
        if args.image:
            if os.path.isfile(args.image):
                self.image = args.image
            elif os.path.isfile(os.path.join(args.directory, args.image)):
                self.image = os.path.join(args.directory, args.image)
            else:
                raise RuntimeError(f"Specified image {args.image} not found")
            # Sanity check on specified image, use same requirements or require
            # user manually override this check when specifying image
            if not (Artwork._UsableResolution(self.image) or args.forceimage):
                raise InvalidArtworkFormatError("Specified image either too small or incorrect aspect ratio")
            return
        self.image = filename
        if os.path.isfile(filename):
            logging.info("Using %s as image source", self.image)
            return
        # This method searches for an image, if it finds one then it copies/extracts
        # it to ``filename`` which means that ``os.path.isfile(filename)`` now returns
        # True, but we need to clean up the file we created.
        self.owns_image = True
        atexit.register(Artwork.Clean, self)
        self._FindImage(isinstance(mdata, metadata.AlbumMetadata))

    def Clean(self):
        if self.owns_image and os.path.exists(self.image):
            logging.info("Deleting %s", self.image)
            os.unlink(self.image)

    def ImageType(self):
        """Returns the lower case version of the image extension, either 'png' or 'jpg'"""
        return self.image[self.image.rfind('.') + 1:].lower()

    def _SwitchToPNG(self):
        """Assumes that the image name is a JPG file, converts to point to PNG."""
        self.image = self.image.replace(ext.JPG, ext.PNG)
        assert self.image.endswith(ext.PNG)

    @staticmethod
    def _UsableResolution(filename):
        """Requires the image satisfy the following requirements:
         - At least 500x500 pixels
         - Aspect ratio between 0.99 and 1.01

        :param: ``filename`` [str], path to image file
        :returns: [tuple[bool, int]] where
                   bool: Describes whether the image satisfies the criteria
                   int: Image width, useful for finding the largest image
        """
        with Image.open(filename, 'r') as img:
            # Remove small images:
            if min(img.width, img.height) < 500:
                logging.debug('Skipping %s since dimensions are %dx%d', filename, img.width, img.height)
                return 0
            aspect = img.width / img.height
            # Remove images which aren't approximately square:
            if aspect < 0.99 or aspect > 1.01:
                logging.debug('Skipping %s since aspect ratio is %0.3f:1', filename, img.width/img.height)
                return 0
            # Consider image usable
            logging.debug('Considering %s', filename)
            return img.width

    def _FindImage(self, excludemerged):
        """This method is called in the case that the image file wasn't readily
        found.  It creates a copy of some other image file or tries to extract
        from FLAC files.

        Preference is for a file named ``folder.jpg``, ``cover.jpg``, or
        ``front.jpg``, then any JPG/JPEG file which is not hidden so long as
        it is the only such image file, and then attempts to extract attached
        images from the FLAC files in the directory.
        """
        directory = flacutil.DirectoryName(self.image) or os.getcwd()
        logging.debug('Searching in directory %s', directory)
        images = {}
        for f in flacutil.GetFilenames(ext.IMAGES, directory):
            logging.debug('Found file %s', f)
            width = Artwork._UsableResolution(f)
            if width:
                images[width] = f
        if images:
            logging.debug('Found %s files', len(images))
            largest_image = images[max(images)]
            if largest_image.endswith(ext.PNG):
                self._SwitchToPNG()
            shutil.copy(largest_image, self.image)
            logging.info("Using %s as image source", largest_image)
            return
        # Last resort is to check for embedded images within the FLAC files
        # If the merging has already happened, which it no longer does but
        # used to, then we will need to exclude the merged file since it
        # does not have any metadata.
        # NB: Since obtaining the FLAC files is checked elsewhere there's no need
        #     to worry about if ``flacutil.GetFilenames`` returns ``[]``, so we
        #     should be able to just reference the first element successfully.
        #     If not it will cause an ``IndexError``.
        exclude = [self.image.replace(ext.JPG, ext.FLAC)] if excludemerged else []
        flac_file = flacutil.GetFilenames(ext.FLAC, directory, exclude=exclude)[0]
        cmd = [flacutil.METAFLAC_EXE, f'--export-picture-to={self.image}', flac_file]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            raise FileNotFoundError("Could not find artwork image; specify with --image option")
        with Image.open(self.image, 'r') as img:
            if img.format == 'PNG':
                # Actually contained a PNG image
                self._SwitchToPNG()
            elif img.format != "JPEG":
                raise InvalidArtworkFormatError(f"Expected JPG/PNG artwork, found {img.format}")
        # Returns a tuple of ``(bool, int)`` describing whether to use the image
        # and if it is usable, the resolution (width).  Here we only need the boolean
        # status of whether to use the image or not, so we test on the first element.
        if not Artwork._UsableResolution(self.image):
            # Since ownership is already taken and the ``Clean`` method has been registered
            # via the ``atexit`` module we don't need to worry about cleaning up the file
            # that was extracted ourselves and can just raise the exception.
            raise InvalidArtworkFormatError("Embedded artwork is either too small or has wrong aspect ratio")
        logging.info("Using embedded %s artwork from %s", self.ImageType(), flac_file)
