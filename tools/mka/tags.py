"""Slightly more human readable tags for XML parsing.
Exists mainly to prevent making a typo compared to
using string literals.
"""
# High level tags for MatroskaTagger
Tags = "Tags"
Tag = "Tag"
Targets = "Targets"
TargetTypeValue = "TargetTypeValue"
ChapterUID = "ChapterUID"
Simple = "Simple"
Name = "Name"
String = "String"

# Elements for MatroskaTagger
TotalParts = "TOTAL_PARTS"
PartNumber = "PART_NUMBER"
Artist = "ARTIST"
Title = "TITLE"
Side = "SIDE"
Subindex = "SUBINDEX"
Phase = "PHASE"
Subtitle = "SUBTITLE"

# High level tags for MatroskaChapters
Chapters = "Chapters"
EditionEntry = "EditionEntry"
EditionUID = "EditionUID"
ChapterAtom = "ChapterAtom"

# Elements for MatroskaChapters
ChapterPhysEquiv = "ChapterPhysicalEquiv"
ChapterDisplay = "ChapterDisplay"
ChapterString = "ChapterString"
ChapterTime = "ChapterTimeStart"

track_tags = {'title': Title,
              'track': PartNumber,
              'side': Side,
              'subindex': Subindex,
              'subtitle': Subtitle,
              'phase': Phase}

class TargetTypes:
    # These are only in a class to create scope
    Collection = "70"
    MultiDisc = "60"
    Album = "50"
    Session = "40"
    Track = "30"
    Subtrack = "20"


class PhysicalEquiv:
    # These are only in a class to create scope
    Set = "70"
    Album = "60"
    Side = "50"
    Session = "30"
    Track = "20"
    Subtrack = "10"
