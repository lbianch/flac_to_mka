import os
import subprocess
import atexit
from logging import getLogger

from tools.util import ext, flacutil, namegen

logging = getLogger(__name__)


def checked(ext):
    """Function to be used as a wrapper for a ``FLACMerger`` member method.
    The wrapper must be called with an ``ext`` parameter to signal which
    file extension is created by the wrapped member method, which returns a
    list of arguments to be executed via ``subprocess.run``.  If the external
    tool signals an error then any temporary output would be deleted and the
    error is re-raised.
    """
    def wrap(func):
        def wrapped(self):
            self._delfile(ext)
            args = func(self)
            try:
                subprocess.run(args, check=True)
            except subprocess.CalledProcessError:
                self._delfile(ext)
                raise
        return wrapped
    return wrap


class FLACMerger:
    """Class to handle merging of FLAC files.  A file list is provided
    in the constructor, and the ``Create`` method may be used to begin
    merging.  Intermediate output to WAV is also provided via ``MergeWAV``.
    Encoding of the optional intermediate WAV is available via ``Encode``,
    which uses the best compression available in FLAC.

    Requires: SOX, optionally FLAC (for two-step merging then encoding)
      Location of SOX and FLAC configurable via ``config.yaml`` used in
      ``tools.util.flacutil``
      """

    def __init__(self, files, outname=None):
        """Accepts a list of file names, either absolute or relative paths, and
        an optional ``outname`` parameter which is either a ``str`` or a
        ``namegen.FileName``.
        """
        self.files = files
        self.outname = namegen.GetNamegen(outname)
        atexit.register(FLACMerger.Clean, self)

    def _delfile(self, extension):
        if os.path.exists(self.outname(extension)):
            logging.info("Deleting %s", self.outname(ext))
            os.unlink(self.outname(extension))

    def Clean(self):
        """Deletes any generated FLAC file."""
        self._delfile(ext.FLAC)

    def Create(self, outname=None):
        """Performs direct merging of FLAC files.  Output file name can
        be explicitly set via the ``outname`` parameter.  If no output
        name parameter has been set, either in this method or in the
        constructor, then this method will raise a ``RuntimeError.``
        """
        if outname:
            self.outname = namegen.GetNamegen(outname)
        if not self.outname:
            raise RuntimeError("Output name must be set.")
        self.MergeFLAC()

    @checked(ext.FLAC)
    def MergeFLAC(self):
        """Raw access to direct FLAC merging.  Output file name must be
        set via the constructor.
        """
        return [flacutil.SOX_EXE] + self.files + [self.outname(ext.FLAC)]

    @checked(ext.WAV)
    def MergeWAV(self):
        """Optional two-step encoding allows merging of FLAC files into intermediate
        WAV file.  Output file name must be set via the constructor.
        """
        return [flacutil.SOX_EXE] + self.files + [self.outname(ext.WAV)]

    @checked(ext.FLAC)
    def Encode(self):
        """Optional two-step encoding requires the intermediate WAV file to already
        exist.  Output file name must be set via the constructor.
        """
        return [flacutil.FLAC_EXE, "--best", self.outname(ext.WAV)]
