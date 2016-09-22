import os
import atexit
import contextlib
import xml.etree.ElementTree as ET
from logging import getLogger
from collections import defaultdict

from tools.mka import chapterid, tags
from tools.flac import metadata

logging = getLogger(__name__)


# XML doesn't need to be easily human readable, but
# for debugging purposes it is nice to have.  This can
# easily be switched off by setting ``PRETTYXML = False``
PRETTYXML = True


def PrettifyXML(xml_str):
    if PRETTYXML:
        from xml.dom import minidom
        tmp = minidom.parseString(xml_str)
        xml_str = tmp.toprettyxml()
    return xml_str


class MatroskaTagger:
    def __init__(self, mdata, outputname=None):
        self.metadata = metadata.GetMetadata(mdata)
        self.root = ET.Element(tags.Tags)
        self.ids = chapterid.RandomChapterID(len(mdata.tracks))
        self.outputname = outputname
        self.CreateTags()
        atexit.register(MatroskaTagger.Clean, self)

    def Clean(self):
        if os.path.exists(self.outputname):
            logging.info("Deleting {}".format(self.outputname))
            os.unlink(self.outputname)

    @staticmethod
    def CreateSimpleTag(tag, name, string):
        tag = ET.SubElement(tag, tags.Simple)
        ET.SubElement(tag, tags.Name).text = name
        ET.SubElement(tag, tags.String).text = string

    @staticmethod
    def CreateNestedTag(tag, name1, name2):
        return ET.SubElement(ET.SubElement(tag, name1), name2)

    def GetChapterUID(self, num):
        return str(self.ids[num])
    
    def CreateTotalDiscTag(self):
        if self.metadata.discs < 2:
            return
        tag = ET.SubElement(self.root, tags.Tag)
        MatroskaTagger.CreateNestedTag(tag, tags.Targets, tags.TargetTypeValue).text = tags.TargetTypes.MultiDisc
        MatroskaTagger.CreateSimpleTag(tag, tags.TotalParts, str(self.metadata.discs))

    def CreateMetadata(self):
        discinfo = ET.SubElement(self.root, tags.Tag)
        MatroskaTagger.CreateNestedTag(discinfo, tags.Targets, tags.TargetTypeValue).text = tags.TargetTypes.Album
        for data in self.metadata.items():
            MatroskaTagger.CreateSimpleTag(discinfo, *data)

    def CreateArtistTag(self):
        tag = ET.SubElement(self.root, tags.Tag)
        MatroskaTagger.CreateNestedTag(tag, tags.Targets, tags.TargetTypeValue).text = tags.TargetTypes.Track
        MatroskaTagger.CreateSimpleTag(tag, tags.Artist, self.metadata["ARTIST"])

    def CreateDiscTags(self):
        # Execution of ``CreateTags`` wants this function to exist for a subclass
        pass

    def CreateTrackTag(self, trackno, track):
        if not isinstance(track, dict):
            raise TypeError("Expected track to be a dict, was {}".format(type(track)))
        logging.debug('Creating tag for track: {}'.format(track))
        node = ET.SubElement(self.root, tags.Tag)
        targets = ET.SubElement(node, tags.Targets)
        ET.SubElement(targets, tags.TargetTypeValue).text = tags.TargetTypes.Track
        ET.SubElement(targets, tags.ChapterUID).text = self.GetChapterUID(trackno)
        for key, tag in tags.track_tags.items():
            with contextlib.suppress(KeyError):
                self.CreateSimpleTag(node, tag, str(track[key]))

    def CreateTags(self):
        self.CreateTotalDiscTag()
        self.CreateMetadata()
        self.CreateDiscTags()
        self.CreateArtistTag()
        for track in enumerate(self.metadata.tracks):
            self.CreateTrackTag(*track)

    def Create(self, outputname=None):
        if outputname is not None:
            self.outputname = outputname
        xml = ET.tostring(self.root, encoding="unicode")
        xml = PrettifyXML(xml)
        with open(self.outputname, "w") as out:
            out.write('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n')
            out.write('<!DOCTYPE Tags SYSTEM "matroskatags.dtd">\n')
            out.write(xml)


class MultiDiscTagger(MatroskaTagger):
    def __init__(self, mdata, outputname=None):
        # Build up disc numbers and track numbers
        # eg, discinfo = {'1': 10, '2': 5}
        # for 10 tracks disc 1, 5 tracks disc 2
        # NB: super().__init__ will create the tags and
        #  call CreateMetadata, so this needs to be
        #  defined before super().__init__, but can't
        #  yet use self.metadata so just use mdata 
        def GetDisc(track_info):
            try:
                return '{}{}'.format(track_info['disc'], track_info['side'])
            except KeyError:
                return track_info['disc']

        self.discinfo = defaultdict(list)
        for track in mdata.tracks:
            disc = MultiDiscTagger.GetDisc(track)
            trackno = int(track['track'])
            self.discinfo[disc].append(trackno)
        for key in self.discinfo:
            self.discinfo[key] = max(self.discinfo[key])
        # Because there may be sides, this isn't just ``len(self.discinfo)``
        mdata.discs = max(int(x['disc']) for x in mdata.tracks)
        logging.debug('Disc info: {}'.format(self.discinfo))
        super().__init__(mdata, outputname)

    def CreateDiscTag(self, disc_number, chapter_idxs):
        node = ET.SubElement(self.root, tags.Tag)
        targets = ET.SubElement(node, tags.Targets)
        ET.SubElement(targets, tags.TargetTypeValue).text = tags.TargetTypes.Album
        for chapter_idx in chapter_idxs:
            ET.SubElement(targets, tags.ChapterUID).text = self.GetChapterUID(chapter_idx)
        self.CreateSimpleTag(node, tags.PartNumber, disc_number)
        self.CreateSimpleTag(node, tags.TotalParts, str(len(chapter_idxs)))

    def CreateDiscTags(self):
        discs = defaultdict(list)
        for chapter_idx, track in enumerate(self.metadata.tracks):
            disc = int(track['disc'])
            discs[disc].append(chapter_idx)
        for disc in discs:
            self.CreateDiscTag(disc, discs[disc])


def CreateMatroskaTagger(args, mdata, outname=None):
    cls = MultiDiscTagger if args.multidisc else MatroskaTagger
    return cls(mdata, outname)
