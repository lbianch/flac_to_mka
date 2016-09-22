import os
import atexit
import xml.etree.ElementTree as ET
from logging import getLogger

from tools.mka import chapterid, tags
from tools.flac import metadata
from tools.mka.tagwriter import PrettifyXML

logging = getLogger(__name__)


class MatroskaChapters:
    def __init__(self, mdata, outputname=None):
        self.metadata = metadata.GetMetadata(mdata)
        self.root = ET.Element(tags.Chapters)
        self.edition = ET.SubElement(self.root, tags.EditionEntry)
        self.ids = chapterid.RandomChapterID(len(mdata.tracks))
        self.outputname = outputname
        self.CreateTags()
        atexit.register(MatroskaChapters.Clean, self)

    def Clean(self):
        if os.path.exists(self.outputname):
            logging.info("Deleting %s", self.outputname)
            os.unlink(self.outputname)

    @staticmethod
    def CreateElement(node, name, value):
        ET.SubElement(node, name).text = value

    @staticmethod
    def CreateNestedElement(node, name1, name2, value):
        ET.SubElement(ET.SubElement(node, name1), name2).text = value

    def GetChapterUID(self, num):
        return str(self.ids[num])

    def CreateEdition(self):
        # RandomChapterIDs allows 0..n-1 for the chapters and -1 for the track itself
        # NB: Track here means Matroska track, ie, the single (merged) FLAC file
        MatroskaChapters.CreateElement(self.edition, tags.EditionUID, self.GetChapterUID(-1))

    def CreateTrackTag(self, trackno, track):
        node = ET.SubElement(self.edition, tags.ChapterAtom)
        MatroskaChapters.CreateElement(node, tags.ChapterUID, self.GetChapterUID(trackno))
        MatroskaChapters.CreateElement(node, tags.ChapterPhysEquiv, tags.PhysicalEquiv.Track)
        try:
            title = '{}: {}'.format(track['title'], track['subtitle'])
        except KeyError:
            title = track['title']
        MatroskaChapters.CreateNestedElement(node, tags.ChapterDisplay, tags.ChapterString, title)
        MatroskaChapters.CreateElement(node, tags.ChapterTime, track['start_time'])
            
    def CreateTags(self):
        self.CreateEdition()
        for track in enumerate(self.metadata.tracks):
            self.CreateTrackTag(*track)

    def Create(self, outputname=None):
        self.outputname = outputname or self.outputname
        xml = ET.tostring(self.root, encoding="unicode")
        xml = PrettifyXML(xml)
        with open(self.outputname, "w") as out:
            out.write('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n')
            out.write('<!DOCTYPE Tags SYSTEM "matroskachapters.dtd">\n')
            out.write(xml)
