import atexit
import contextlib
import os
from logging import getLogger

import mutagen.flac

from tools.util import ext, flacutil, namegen, time

logging = getLogger(__name__)
IgnoreKeyError = contextlib.suppress(KeyError)

valid_tags = ["GENRE", "VERSION", "DISC_NAME", "LABEL", "ISSUE_DATE"]

class CueSheet:
    """Class which accepts a list of FLAC file names and a
    ``metadata.AlbumMetadata`` object and produces a CUE
    sheet.  To be embedded within the output MKA file but
    not used as a source for chapters.  Purpose is to enable
    extraction of the FLAC + CUE in order to enable writing
    to CD with minimal effort.
    """

    # TODO: This doesn't need ``files`` as we cau use ``mdata.source``
    def __init__(self, files, mdata):
        self.files = files
        self.metadata = mdata
        self.mergedfile = mdata.GetOutputFilename()
        self.outputname = namegen.GetNamegen(self.mergedfile)(ext.CUE)
        self.cuesheet = []
        self.CreateCUE()
        atexit.register(CueSheet.Clean, self)

    def Clean(self):
        if os.path.exists(self.outputname):
            logging.info("Deleting %s", self.outputname)
            os.unlink(self.outputname)

    def CreateCUE(self):
        self.cuesheet.append('PERFORMER "{}"'.format(self.metadata["ARTIST"]))
        self.cuesheet.append('TITLE "{}"'.format(self.metadata["TITLE"]))
        self.cuesheet.append('REM DATE "{}"'.format(self.metadata["DATE_RECORDED"]))
        for tag in valid_tags:
            with IgnoreKeyError:
                self.cuesheet.append('REM {} "{}"'.format(tag, self.metadata[tag]))
        self.cuesheet.append('FILE "{}" WAVE'.format(self.mergedfile))

        track_time = time.Time()
        for track_num, f in enumerate(self.files):
            data = mutagen.flac.FLAC(f)
            self.cuesheet.append('  TRACK {} AUDIO'.format(str(track_num + 1).zfill(2)))
            try:
                title = '{}: {}'.format(data["TITLE"][0], data["SUBTITLE"][0])
            except KeyError:
                title = data["TITLE"][0]
            self.cuesheet.append('    TITLE "{}"'.format(title))
            self.cuesheet.append('    PERFORMER "{}"'.format(self.metadata["ARTIST"]))
            self.cuesheet.append('    INDEX 01 {}'.format(track_time.CueCode()))
            track_time += data.info.length  # seconds

    def Create(self, outputname=None):
        self.outputname = outputname or self.outputname
        with open(self.outputname, "w") as out:
            out.write('\n'.join(self.cuesheet))
            out.write('\n')


class CueFilenameChanger:
    """Class used to handle the conversion of a CUE sheet to another CUE
    sheet.  Used by ``tools.cue``, when the specified directory to convert
    to MKA contains FLAC+CUE.  Alters the "FILENAME" line in the CUE sheet
    and removes any remark lines.
    """

    def __init__(self, cuesheet, outputcue):
        """Performs conversion of CUE sheet, and registers the output CUE
        sheet to be automatically deleted upon program exit via the
        ``atexit`` module.

        :param: ``cuesheet`` [str]: hold the name of the original CUE sheet.
        :param: ``outputcue`` [str]: holds the name of the to-be-created CUE sheet.
        """
        self.createdfile = None
        self.lines = []
        if cuesheet != outputcue:
            logging.info("%s -> %s", cuesheet, outputcue)
            self.createdfile = outputcue
            self._create(cuesheet)
            self._write()
        atexit.register(CueFilenameChanger.Clean, self)

    def Clean(self):
        if self.createdfile:
            logging.info("Deleting %s", self.createdfile)
            os.unlink(self.createdfile)

    @staticmethod
    def _keep_line(line):
        line = line.lstrip()
        if not line.startswith("REM"):
            return True
        line = line[4:]
        for tag in ["DATE"] + valid_tags:
            if line.startswith(tag):
                return True
        return False

    def _create(self, source_cue):
        with open(source_cue) as source_cue:
            self.lines = source_cue.read().split("\n")
        self.lines = filter(CueFilenameChanger._keep_line, self.lines)
        self.lines = list(self.lines)
        for idx, line in enumerate(self.lines):
            if line.startswith("FILE "):
                filename = self.createdfile.replace(ext.CUE, ext.WAV)
                filename = flacutil.FileName(filename)
                self.lines[idx] = 'FILE "{}" WAVE'.format(filename)
            elif '"' in line:
                line = line.split('"')
                if line[1].strip():
                    self.lines[idx] = '{} "{}"'.format(line[0].rstrip(), line[1].strip())
                else:
                    self.lines[idx] = None
        self.lines = filter(None, self.lines)

    def _write(self):
        with open(self.createdfile, "w") as outputcue:
            outputcue.write('\n'.join(self.lines))
            outputcue.write('\n')
