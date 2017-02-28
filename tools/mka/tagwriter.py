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
    return xml_str.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8" ?>')


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
            logging.info("Deleting %s", self.outputname)
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

    def CreateMetadata(self):
        discinfo = ET.SubElement(self.root, tags.Tag)
        MatroskaTagger.CreateNestedTag(discinfo, tags.Targets, tags.TargetTypeValue).text = tags.TargetTypes.Album
        for data in self.metadata.items():
            msg = 'Creating generic TargetTypeValue %s metadata tag using %s'
            logging.debug(msg, tags.TargetTypes.Album, list(data))
            MatroskaTagger.CreateSimpleTag(discinfo, *data)

    def CreateArtistTag(self):
        tag = ET.SubElement(self.root, tags.Tag)
        MatroskaTagger.CreateNestedTag(tag, tags.Targets, tags.TargetTypeValue).text = tags.TargetTypes.Track
        MatroskaTagger.CreateSimpleTag(tag, "ARTIST", self.metadata["ARTIST"])

    def CreateDiscTags(self):
        # Execution of ``CreateTags`` wants this function to exist for a subclass
        pass

    def CreateTrackTag(self, trackno, track):
        if not isinstance(track, dict):
            raise TypeError(f"Expected track to be a dict, was {type(track)}")
        logging.debug('Creating tag for track: %s', track)
        node = ET.SubElement(self.root, tags.Tag)
        targets = ET.SubElement(node, tags.Targets)
        ET.SubElement(targets, tags.TargetTypeValue).text = tags.TargetTypes.Track
        ET.SubElement(targets, tags.ChapterUID).text = self.GetChapterUID(trackno)
        for key, tag in tags.track_tags.items():
            with contextlib.suppress(KeyError):
                self.CreateSimpleTag(node, tag, str(track[key]))

    def CreateTags(self):
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
        with open(self.outputname, "w", encoding="utf-8") as out:
            out.write(xml)


class MultiDiscTagger(MatroskaTagger):
    def __init__(self, mdata, outputname=None):
        # Build up disc numbers and track numbers eg, discinfo = {'1': 10, '2': 5}
        # for 10 tracks disc 1, 5 tracks disc 2.
        # For Vinyl, eg: {'1A': 3, '1B': 4, '2A': 4, '2B': 5}
        # NB: super().__init__ will call ``CreateTags``, so this needs to be defined
        #  before super().__init__ as ``CreateDiscTags`` is called via ``CreateTags``
        #  and ``CreateDiscTags`` relies on ``self.discinfo``

        # Create ``self.discinfo`` storing a mapping from discs to ``list[dict]``
        # of the form ``{'index': chapter_index, 'track': track_number}``
        # slightly more readable than ``{chapter_index: track_number}``
        self.discinfo = defaultdict(list)
        for chapter_idx, track in enumerate(mdata.tracks):
            disc = metadata.GetDisc(track)
            data = {'index': chapter_idx, 'track': track['track']}
            self.discinfo[disc].append(data)
        # Because there may be sides, this isn't just ``len(self.discinfo)``
        self.discs = max(int(x['disc']) for x in mdata.tracks)
        logging.debug('Disc info: %s', self.discinfo)
        super().__init__(mdata, outputname)

    def CreateDiscTag(self, disc_number, chapter_idxs):
        """Creates a tag describing the disc-level data, specifically
        the number of tracks associated with the disc, a list of chapters,
        and the disc name.
        Input parameter `disc_number` is a `str` which should contain only
        numbers and the letters 'A' or 'B'.  If sides are present, they are
        stripped.  As an example case, if this is working on a 2 LP release
        then there are discs '1A', '1B', '2A', and '2B', and there would be
        two entries for `PartNumber = 1` with distinct sets of chapters.
        It is possible each side has a different disc name, if any.
        """
        node = ET.SubElement(self.root, tags.Tag)
        targets = ET.SubElement(node, tags.Targets)
        ET.SubElement(targets, tags.TargetTypeValue).text = tags.TargetTypes.Album
        for chapter_idx in chapter_idxs:
            chapter_idx = chapter_idx['index']
            ET.SubElement(targets, tags.ChapterUID).text = str(self.GetChapterUID(chapter_idx))
        self.CreateSimpleTag(node, tags.PartNumber, disc_number.strip('AB'))  # Remove side if present
        # This needs to find the number of tracks for this disc
        total_parts = max(int(ch['track']) for ch in chapter_idxs)
        self.CreateSimpleTag(node, tags.TotalParts, str(total_parts))
        if disc_number in self.metadata.disc_data:
            name = self.metadata.disc_data[disc_number]
            self.CreateSimpleTag(node, "DISC_NAME", name)

    def CreateDiscTags(self):
        for disc in sorted(self.discinfo):
            self.CreateDiscTag(disc, self.discinfo[disc])

    def CreateMetadata(self):
        tag = ET.SubElement(self.root, tags.Tag)
        MatroskaTagger.CreateNestedTag(tag, tags.Targets, tags.TargetTypeValue).text = tags.TargetTypes.MultiDisc
        MatroskaTagger.CreateSimpleTag(tag, tags.TotalParts, str(self.discs))
        super().CreateMetadata()


def CreateMatroskaTagger(args, mdata, outname=None):
    cls = MultiDiscTagger if args.multidisc else MatroskaTagger
    return cls(mdata, outname)
