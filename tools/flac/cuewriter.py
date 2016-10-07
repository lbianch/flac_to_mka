import atexit
import contextlib
import os
from logging import getLogger

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

    def __init__(self, mdata):
        self.metadata = mdata
        self.files = mdata.source
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
                # NB: Use `metadata.data[tag]` because it will `raise KeyError` while
                #     `metadata[tag]` is an alias to `metadata.get(tag, '')`
                self.cuesheet.append('REM {} "{}"'.format(tag, self.metadata.data[tag]))
        self.cuesheet.append('FILE "{}" WAVE'.format(self.mergedfile))

        for track_num, track in enumerate(self.metadata.tracks):
            self.cuesheet.append('  TRACK {} AUDIO'.format(str(track_num + 1).zfill(2)))
            try:
                title = '{}: {}'.format(track["title"], track["subtitle"])
            except KeyError:
                title = track["title"]
            self.cuesheet.append('    TITLE "{}"'.format(title))
            self.cuesheet.append('    PERFORMER "{}"'.format(self.metadata["ARTIST"]))
            # Need to convert mka time code from track["start_time"] to a CUE sheet code
            time_code = time.MKATimeToCueTime(track["start_time"])
            self.cuesheet.append('    INDEX 01 {}'.format(time_code))

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
        return any(line.startswith(tag) for tag in ["DATE"] + valid_tags)

    def _create(self, source_cue):
        with open(source_cue) as source_cue:
            lines = source_cue.read().split("\n")
        lines = filter(CueFilenameChanger._keep_line, lines)
        for idx, line in enumerate(lines):
            if line.startswith("FILE "):
                filename = self.createdfile.replace(ext.CUE, ext.WAV)
                filename = flacutil.FileName(filename)
                self.lines.append('FILE "{}" WAVE'.format(filename))
            elif '"' in line:
                line = line.split('"')[0:2]
                if not line[1].strip():
                    continue
                self.lines.append('{} "{}"'.format(*map(str.rstrip, line)))
            else:
                self.lines.append(line)
        self.lines = filter(None, self.lines)

    def _write(self):
        with open(self.createdfile, "w") as outputcue:
            outputcue.write('\n'.join(self.lines))
            outputcue.write('\n')
