import atexit
import contextlib
import os
from logging import getLogger
from itertools import chain

from tools.util import ext, flacutil, namegen, time

logging = getLogger(__name__)
IgnoreKeyError = contextlib.suppress(KeyError)

VALID_TAGS = ["GENRE", "VERSION", "DISC_NAME", "LABEL", "ISSUE_DATE"]


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
        cuesheet = [f'PERFORMER "{self.metadata["ARTIST"]}"',
                    f'TITLE "{self.metadata["TITLE"]}"',
                    f'REM DATE "{self.metadata["DATE_RECORDED"]}"']
        for tag in VALID_TAGS:
            with IgnoreKeyError:
                # NB: Use `metadata.data[tag]` because it will `raise KeyError` while
                #     `metadata[tag]` is an alias to `metadata.get(tag, '')`
                cuesheet.append(f'REM {tag} "{self.metadata.data[tag]}"')
        cuesheet.append(f'FILE "{self.mergedfile}" WAVE')

        for track_num, track in enumerate(self.metadata.tracks):
            cuesheet.append(f'  TRACK {track_num+1:02} AUDIO')
            try:
                cuesheet.append(f'    TITLE "{track["title"]}: {track["subtitle"]}"')
            except KeyError:
                cuesheet.append(f'    TITLE "{track["title"]}"')
            cuesheet.append(f'    PERFORMER "{self.metadata["ARTIST"]}"')
            # Need to convert mka time code from track["start_time"] to a CUE sheet code
            cuesheet.append(f'    INDEX 01 {time.MKATimeToCueTime(track["start_time"])}')
        self.cuesheet = cuesheet

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
        if line.startswith('REM'):
            return any(tag in line for tag in chain(["DATE"], VALID_TAGS))
        return bool(line)

    def _process_line(self, line):
        if line.startswith("FILE "):
            filename = self.createdfile.replace(ext.CUE, ext.WAV)
            filename = flacutil.FileName(filename)
            return f'FILE "{filename}" WAVE'
        if '"' in line:
            line = [x.rstrip() for x in line.split('"')[0:2]]
            return line[1].lstrip() and f'{line[0]} "{line[1]}"'
        return line

    def _create(self, source_cue):
        with open(source_cue) as source_cue:
            lines = source_cue.readlines()
        lines = map(str.rstrip, lines)
        lines = map(self._process_line, filter(self._keep_line, lines))
        self.lines = list(filter(None, lines))

    def _write(self):
        if self.createdfile is None:
            return
        with open(self.createdfile, "w", encoding="utf8") as outputcue:
            outputcue.write('\n'.join(self.lines))
