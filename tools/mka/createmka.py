import os
import subprocess
from logging import getLogger

from tools.util import ext, flacutil, namegen
logging = getLogger(__name__)


class MKACreator:
    def __init__(self, args, mdata, sourcename, artwork):
        self.sourcename = namegen.GetNamegen(sourcename)
        self.mkafile = MKACreator._GetOutputFilename(args, flacutil.FileName(self.sourcename()))
        self.title = mdata["TITLE"]
        self.cmd = []
        self.artwork = artwork
        self.BuildCommand()

    def BuildCommand(self):
        cmd = [flacutil.MKVMERGE_EXE, "-o", self.mkafile, "--title", self.title,
               "--default-track", "0:yes", "--forced-track", "0:no", "-a", "0",
               "-D", "-S", "-T", "--no-global-tags", "--no-chapters",
               "(", self.sourcename(ext.FLAC), ")", "--track-order", "0:0"]
        # Attach CUE sheet if it exists, if not don't worry since it may be
        # a non-CD format or a multidisc conversion
        if os.path.exists(self.sourcename(ext.CUE)):
            cmd += MKACreator._AttachFile("text/plain", self.sourcename(ext.CUE), self.sourcename.EmbedName(ext.CUE))
        # Attachment for Artwork
        cmd += self._AttachImage()
        # Add chapters and tags from XML files
        cmd += ["--chapters", self.sourcename(ext.CHAPTERS),
                "--global-tags", self.sourcename(ext.XML)]
        self.cmd = cmd

    def Create(self):
        self.cmd or self.BuildCommand()
        subprocess.check_call(self.cmd)

    @staticmethod
    def _GetOutputFilename(args, basename):
        # If we were given an explicit output file name, use it
        if args.output and os.path.isfile(args.output):
            return args.output
        mkafile = "{} [FLAC]{}".format(basename, ext.MKA)
        # If we were given an explicit output directory, use that
        if args.output and os.path.isdir(args.output):
            return os.path.join(args.output, mkafile)
        # Use the system default output directory, configurable
        # in ``config.yaml``
        return os.path.join(flacutil.OUTPUTDIR, mkafile)

    @staticmethod
    def _AttachFile(description, filename, embedname=""):
        if not embedname.strip():
            embedname = filename
        return ["--attachment-mime-type", description, "--attachment-name",
                flacutil.FileName(embedname), "--attach-file", filename]

    def _AttachImage(self):
        file_types = {"jpg": ["image/jpeg", ext.JPG], "png": ["image/png", ext.PNG]}
        try:
            file_type = file_types[self.artwork.ImageType()]
        except KeyError:
            raise ValueError("Expected 'jpg' or 'png', but found '{}'".format(self.artwork.ImageType()))
        return MKACreator._AttachFile(file_type[0], self.artwork.image, self.sourcename.EmbedName(file_type[1]))
