import contextlib
import os.path
import re
from abc import ABC, abstractmethod
from collections import OrderedDict
from logging import getLogger

import mutagen.flac

from flac_to_mka.flac import arguments
from flac_to_mka.util import ext, time


FLACTime = time.Time
logging = getLogger(__name__)
IgnoreKeyError = contextlib.suppress(KeyError)


class TagNotFoundError(Exception):
    pass


class CueFormatError(Exception):
    pass


class DiscConfigurationError(Exception):
    pass


class Metadata(ABC):
    """Class for holding information about an album, but not specifying a
    method by which to obtain the information.  Intended as a parent class
    for other classes which implement the ability to pull track-level metadata.

    Required tags are 'TITLE', 'ARTIST', 'GENRE', and 'DATE' ('DATE_RECORDED').
    Stores a ``list`` of tracks in ``self.tracks``, which are intended to be
    ``dict`` objects holding data with string keys and values, intended to
    have the keys 'title', 'track', 'start_time', and optionally 'disc', 'side',
    'phase', 'subindex', and/or 'subtitle'.  The 'start_time' parameter is used by
    ``mka.chapterwriter.MatroskaChapters`` to write out the chapter information
    to be used as the Matroska chapter source (XML).

    Performs some validation against optional parameters args, which takes
    priority.  Only allows the disc-level tag 'DISCNUMBER' if 'DISCTOTAL' is
    also present (for CUE sheets, this is 'REM DISC' and 'REM DISCS').

    Also supports 1.0 and 5.1 audio which is indicated in the output file name,
    unless explicitly overridden with a non-empty ``args.output`` value passed
    to the constructor.
    """

    def __init__(self, source, args):
        self.data = {k: None for k in ["TITLE", "ARTIST", "GENRE", "DATE_RECORDED"]}
        self.channels = '2.0'
        self.discs = 1
        self.tracks = []
        self.filename = None
        self.forced_filename = False
        self.source = source

        self._initialize(args)
        tag = self._GetTag()
        self._PullChannels(tag.info)
        self._PullHDFormat(tag.info)
        self._MergeWithArgs(args)
        self._Validate()
        self._Finalize()

    @abstractmethod
    def _initialize(self, args):
        pass

    @abstractmethod
    def _GetTag(self):
        pass

    @property
    @abstractmethod
    def sumparts(self):
        pass

    def _PullChannels(self, info):
        # Constructor initialized this to '2.0', check if that's accurate
        if info.channels == 6:
            self.channels = '5.1'
        elif info.channels == 1:
            self.channels = '1.0'
        elif info.channels != 2:
            raise RuntimeError(f"Channels {info.channels} not supported")

    def _PullHDFormat(self, info):
        # Pull format information, of the form SampleRate/BitDepth [5.1|1.0]
        # If the format matches the CD specification then nothing is done
        # The result is stored in ``self["HD_FORMAT"]``
        if info.sample_rate == 44100 and info.bits_per_sample == 16 and info.channels == 2:
            return
        # This isn't a CD format
        samplerate = info.sample_rate
        # Want 44.1kHz for 44100, but 48kHz for 48000 rather than 48.0kHz
        hdformat = [str(samplerate/1000) if samplerate % 1000 else str(samplerate//1000), f"/{info.bits_per_sample}"]
        if info.channels == 6:
            hdformat.append(" 5.1")
        elif info.channels == 1:
            hdformat.append(" 1.0")
        self["HD_FORMAT"] = ''.join(hdformat)

    def _MergeWithArgs(self, args):
        """Method to introduce arguments passed in via command line.  These
        arguments take priority over any other extracted information.
        """
        if not args:
            self._Validate()
            return
        if args.album:
            self["TITLE"] = args.album
        if args.artist:
            self["ARTIST"] = args.artist
        if args.genre:
            self["GENRE"] = args.genre
        if args.year:
            self["DATE_RECORDED"] = args.year
        if args.label:
            self["LABEL"] = args.label
        if args.issuedate and "LABEL" in self:
            self["ISSUE_DATE"] = args.issuedate
        if args.version:
            self["VERSION"] = args.version
        if args.medium:
            self["ORIGINAL_MEDIUM"] = args.medium
        # Check for disc numbering, if it encountered a manually
        # set number of discs and the disc is specified then
        # allow it to be altered
        if args.disc and self.discs > 1:
            self["PART_NUMBER"] = args.disc
        # If the disc number was set, but the number of
        # discs was manually passed in, set the disc count
        if args.discs and "PART_NUMBER" in self:
            self.discs = int(args.discs)
        # If both are passed in manually, use them
        if args.disc and args.discs:
            self["PART_NUMBER"] = args.disc
            self.discs = int(args.discs)
        # If disc number and total information was found, but it
        # was requested to parse this as a single disc instead then
        # delete the "PART_NUMBER" information and reset the ``discs``
        if args.nodiscs:
            self.discs = 1
            with IgnoreKeyError:
                del self["PART_NUMBER"]
        # Manually overriding the output file name is handled via a flag
        #if args.output:
        #    self.filename = args.output
        #    self.forced_filename = True
        self._Validate()

    def _Validate(self):
        """Ensures sane entries for "ISSUE_DATE" and "LABEL", disc numbering,
        and ensures that the required tags ("TITLE", "ARTIST", "GENRE", "DATE")
        have been set.  Removes leading or trailing whitespace for all tags.
        """
        # There's some possible conflict with LABEL and ISSUE_DATE
        # If the date exists but the label isn't defined, this property
        # will be ignored
        if ("ISSUE_DATE" in self) != ("LABEL" in self):
            with IgnoreKeyError:
                del self["ISSUE_DATE"]
            with IgnoreKeyError:
                del self["LABEL"]
        # Also check that both disc and discs exists or neither do
        if self.discs > 1 and "PART_NUMBER" not in self:
            raise DiscConfigurationError("Number of discs is set but disc number not known")
        if "PART_NUMBER" in self and self.discs < 2:
            raise DiscConfigurationError("Disc number is set but number of discs is not known")
        # Ensure that the original medium is set, if it hasn't been set yet then assume CD
        if "ORIGINAL_MEDIUM" not in self:
            self["ORIGINAL_MEDIUM"] = "CD"
        elif self["ORIGINAL_MEDIUM"] not in arguments.MEDIUM_CHOICES:
            logging.critical("Invalid medium: '%s' - must be one of %s",
                             self['ORIGINAL_MEDIUM'], arguments.MEDIUM_CHOICES)
            raise ValueError(f"Invalid medium: '{self['ORIGINAL_MEDIUM']}' - must be one of {arguments.MEDIUM_CHOICES}")
        # At this point it is necessary to require that all the metadata is present
        # These were setup in the constructor as ``None`` so they do exist, but they
        # must have been overridden as non-``None`` values
        # ``required_tags`` holds tag keys which map onto descriptions for error output
        required_tags = {"TITLE": "title",
                         "ARTIST": "artist",
                         "GENRE": "genre",
                         "DATE_RECORDED": "year"}
        for tag in required_tags:
            if self[tag] is None:
                raise TagNotFoundError(f"Incomplete metadata - missing {required_tags[tag]}")
        for key, value in self.items():
            self[key] = value.strip()

    def _Finalize(self):
        """``self.sumparts`` is a ``property`` returning a boolean  which controls whether
        the output should contain the "TOTAL_PARTS" field which specifies the number of
        tracks.  This method also ensures the "DATE_RECORDED" field is a 4-digit year.
        Note that when specified, the number of tracks is not simply ``len(self.tracks)``
        but rather the highest numbered track.
        """
        logging.debug("Sumparts = %s", self.sumparts)
        if self.sumparts:
            # Because some files may have corresponded to subtracks of a single logical
            # track, it's possible that the number of items in ``self.tracks`` is greater
            # than the actual number of tracks, so the correct thing to do is take
            # the largest track number
            logging.debug("Summing parts")
            self["TOTAL_PARTS"] = str(max(int(x["track"]) for x in self.tracks))
        elif "TOTAL_PARTS" in self:
            logging.debug("Deleting 'TOTAL_PARTS'")
            del self["TOTAL_PARTS"]
        else:
            logging.debug("Not summing parts and 'TOTAL_PARTS' doesn't exist")
        if len(self["DATE_RECORDED"]) != 4:
            logging.debug("Improper date found %s", self["DATE_RECORDED"])
            year = re.split("-|/|\.", self["DATE_RECORDED"])
            for y in year:
                if len(y) == 4:
                    logging.debug("Found year %s", y)
                    self["DATE_RECORDED"] = y
                    break
            else:
                raise RuntimeError(f"Can't parse date {self['DATE_RECORDED']}")

    def __getitem__(self, key):
        """If the ``key`` doesn't exist, the empty string is returned.
        As though ``__getitem__(key)`` was really ``get(key, "")``.
        NB: Don't want to use a ``defaultdict`` for ``self.data`` since
            that would actually store new keys when they're accessed.
        """
        return self.data.get(key, '')

    def items(self):
        return self.data.items()

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __str__(self):
        """String representation of the disc-level metadata.  Produces a
        table with the metadata which can be printed.  Note that track-level
        information is not part of the table.
        """
        # These are required tags so we should have generated an
        # error beforehand and this shouldn't raise a ``KeyError``
        s = [("Album Title", self["TITLE"]), ("Album Artist", self["ARTIST"]),
             ("Year", self["DATE_RECORDED"]), ("Genre", self["GENRE"])]
        s = OrderedDict(s)

        def add_optional(key):
            nonlocal s
            if key in self:
                text = key.replace('_', ' ').split(' ')
                text = ' '.join([x.capitalize() for x in text])
                s[text] = self[key]

        add_optional("LABEL")
        add_optional("ISSUE_DATE")
        add_optional("ORIGINAL_MEDIUM")
        add_optional("VERSION")
        add_optional("HD_FORMAT")
        add_optional("DISC_NAME")
        if self.discs > 1:
            s["Disc"] = self["PART_NUMBER"]
            s["Discs"] = self.discs
        if self.channels != "2.0":
            s["Channels"] = self.channels
        # Now we have to deal with the formatted output.  First we need
        # the maximum length of the keys to properly align the output
        # Note that the keys used will have a space appended, so we add 1
        max_len = max(len(x[0]) for x in s)+1

        # Output for an entry in ``s`` of ("Year", "2016") with a ``max_len`` of 10
        # would be: '= Year .....: 2016'
        def line(k, v):
            return f"{k.ljust(max_len, '.')}: {v}"

        s = [line(*x) for x in s.items()]
        # Now we can reuse ``max_len`` to mean the longest fully formatted line
        # We want to add '= ' to the left side and ' =' to the right side to
        # form a border
        max_len = max(len(x) for x in s)
        s = [f'= {x:{max_len}} =' for x in s]
        max_len += 4
        s = [" ALBUM INFORMATION ".center(max_len, "=")] + s + ["=" * max_len]
        return "\n".join(s)

    def GetOutputFilename(self, directory=None):
        """If an explicit filename was provided to command line arguments,
        and ``_MergeWithArgs`` was called, typically via a subclass
        constructor,then that filename is returned.
        Otherwise a name of the form
            Artist - Date - Title (Version) (Disc Disc#) \
            DiscName (Label IssueDate Medium Channels).wav
        is generated, where the parentheses are included only if any
        part inside is non-empty.  The Medium is blank if it is "CD".
        Channels is not filled in if it is "2.0".  Invalid filename
        characters are removed or replaced with dashes.
        """
        if self.forced_filename:
            logging.debug('Forced filename or pre-computed file name = %s', self.filename)
            return self.filename

        tags = dict()

        # Base tag
        tags['base'] = f"{self['ARTIST']} - {self['DATE_RECORDED']} - {self['TITLE']}"

        # Setup version subinfo
        tags['version'] = f" ({self['VERSION']})" if self["VERSION"] else ""

        # Setup label / release subinfo
        channels = self.channels if self.channels != '2.0' else ''
        if self["ORIGINAL_MEDIUM"] == "CD":
            labeltag = f"{self['LABEL']} {self['ISSUE_DATE']} {channels}"
        else:
            labeltag = f"{self['LABEL']} {self['ISSUE_DATE']} {self['ORIGINAL_MEDIUM']} {channels}"
        labeltag = labeltag.strip()
        tags['label'] = labeltag and f" ({labeltag})"

        # Setup disc tag
        if self["PART_NUMBER"]:
            disctag = f" (Disc {self['PART_NUMBER']}) {self['DISC_NAME']}"
        else:
            disctag = f" {self['DISC_NAME']}"
        tags['disc'] = disctag.rstrip()

        # Merge into filename
        filename = f"{tags['base']}{tags['version']}{tags['disc']}{tags['label']}{ext.WAV}"
        # Replace invalid characters with either a dash or remove them
        filename = re.compile("[<>:/\\\\]").sub("-", filename)
        filename = re.compile("[|?*]").sub("", filename)
        # Replace invalid double quotes with valid single quotes
        filename = filename.replace('"', "'")

        if directory:
            return os.path.join(directory, filename)
        return filename

    def _PrintMetadata(self):
        print(str(self))
        for trackno, track in enumerate(self.tracks):
            output = [f"File {str(trackno + 1).zfill(2)}:"]
            with IgnoreKeyError:
                output.append(f"Disc {track['disc']}")
            with IgnoreKeyError:
                output.append(f"Side {track['side']}")
            output.append(f"Track {track['track'].ljust(2)}")
            with IgnoreKeyError:
                output.append(f"Phase {track['phase']}")
            with IgnoreKeyError:
                output.append(f"Subindex {track['subindex']}")
            output.append(f"Time {track['start_time']}")
            try:
                output.append(f'"{track["title"]}: {track["subtitle"]}"')
            except KeyError:
                output.append(f'"{track["title"]}"')
            print(' '.join(output))
        filename = self.GetOutputFilename().replace(ext.WAV, ext.MKA)
        print("Filename:", filename)

    def PrintMetadata(self):
        """Formats and prints the metadata using the string
        representation and adding in track-level details.
        """
        with contextlib.suppress(UnicodeEncodeError):
            self._PrintMetadata()

    def Confirm(self):
        """Prints out metadata using ``PrintMetadata`` then asks
        the user if they want to continue.  Any answer starting
        with 'n' or 'N' is interpreted as "no" while any other
        answer is interpreted as "yes".
        Returns:
            bool: True for user-approved merging, False for cancel
        """
        self.PrintMetadata()
        answer = input("Continue [Y/n]? ").lower()
        return not answer.startswith("n")


def _GetAlbumLevelMetadata(files):
    # Obtain album-level tags from the first file
    # Assumption is these tags are the same for every file
    tag = mutagen.flac.FLAC(files[0])
    # These tags are copied directly
    directmap = ["ARTIST", "GENRE", "LABEL", "ISSUE_DATE",
                 "VERSION", "ORIGINAL_MEDIUM", "DISC_NAME"]
    # These are renamed
    mapping = {"TITLE": "ALBUM", "DATE_RECORDED": "DATE"}
    mapping.update({k: k for k in directmap})
    result = {}
    for rkey, tkey in mapping.items():
        if tkey in tag:
            logging.debug("Found key %s, %s with value %s", rkey, tkey, tag[tkey][0])
            # ``mutagen.flac.FLAC`` behaves like a ``dict[str, list[str]]``
            result[rkey] = tag[tkey][0]
    return result


class AlbumMetadata(Metadata):
    """Metadata class holding information for a collection of FLAC files
    from a single disc.  Searches through the metadata tags in each FLAC
    file to determine information about them then build up the ``Metadata``
    structure.
    Supported disc-level FLAC tags:
      ARTIST, TITLE, DATE, GENRE, LABEL, ISSUE_DATE, VERSION,
      ORIGINAL_MEDIUM, DISC_NAME, DISCTOTAL, DISCNUMBER
    Supported track-level FLAC tags:
      TITLE, TRACKNUMBER, SIDE, SUBINDEX, SUBTITLE, PHASE
    NB: DISCNUMBER is ignored if DISCTOTAL is not present, and vice versa,
    or if both are '1'.

    See parent class ``Metadata`` for more information.
    """

    @property
    def sumparts(self):
        return True

    def _initialize(self, args):
        # First check for multidisc mode; after this we can assume that
        #    ``args.multidisc`` is ``False``
        if args.multidisc:
            raise ValueError("Cannot use 'AlbumMetadata' in multidisc mode, use 'MultidiscMetadata'")

        # Pull in album level data
        data = _GetAlbumLevelMetadata(self.source)
        self.data.update(data)

        # Pull disc number from tags if both fields exist, but skip if disc 1/1
        tag = self._GetTag()
        if "DISCTOTAL" in tag and "DISCNUMBER" in tag:
            discs = int(tag["DISCTOTAL"][0])
            if discs > 1:
                self["PART_NUMBER"] = tag["DISCNUMBER"][0]
                self.discs = discs

        # Pull track-level info: title, subindex, subtitle, start time, phase, side
        mka_time = FLACTime()
        for f in sorted(self.source):
            if self.GetOutputFilename() in f.replace(ext.FLAC, ext.WAV):
                continue
            tag = mutagen.flac.FLAC(f)
            try:
                track = {"title": tag["TITLE"][0],
                         "track": tag["TRACKNUMBER"][0],
                         "start_time": mka_time.MKACode()}
            except KeyError as key:
                raise TagNotFoundError(f"{f} doesn't contain key {key}")
            for t in ["SIDE", "SUBTITLE", "SUBINDEX", "PHASE"]:
                with IgnoreKeyError:
                    track[t.lower()] = tag[t][0]
            self.tracks.append(track)
            mka_time += tag.info.length

    def _GetTag(self):
        return mutagen.flac.FLAC(self.source[0])


def GetDisc(track_info):
    try:
        return f"{track_info['disc']}{track_info['side']}"
    except KeyError:
        return track_info['disc']


class MultidiscMetadata(Metadata):
    """Metadata class holding information for a collection of FLAC files
    from multiple discs.  Searches through the metadata tags in each FLAC
    file to determine information about them then build up the ``Metadata``
    structure.
    Supported collection-level FLAC tags (``self.data``):
      DISCTOTAL, ARTIST, ALBUM TITLE, DATE, GENRE, LABEL,
      ISSUE_DATE,  ORIGINAL_MEDIUM, VERSION
    Supported disc-level FLAC tags (``self.disc_data``):
      DISC_NAME, (Number of tracks is calculated automatically)
    Supported track-level FLAC tags (``self.tracks``):
      TITLE, TRACKNUMBER, SIDE, DISCNUMBER, SUBINDEX, SUBTITLE, PHASE

    See parent class ``Metadata`` for more information.
    """

    def __init__(self, source, args):
        self.disc_data = {}
        super().__init__(source, args)

    @property
    def sumparts(self):
        return False

    def _initialize(self, args):
        logging.debug('tools.flac.metadata.MultidiscMetadata._initialize')
        # First check for multidisc mode; after this we can assume that
        #    ``args.multidisc`` is ``True``
        if not args.multidisc:
            raise ValueError("Cannot use 'MultidiscMetadata' in non-multidisc mode, use 'AlbumMetadata'")

        # Pull in album level data, handling "DISC_NAME" at the
        # disc level, rather than the collection level
        data = _GetAlbumLevelMetadata(self.source)
        with IgnoreKeyError:
            del data["DISC_NAME"]
        self.data.update(data)

        # Now pull track and disc-level information which varies from file to file
        # Track level: track title, subtitle/subindex, start time, disc number
        #              side, and phase
        # Disc level: disc name
        mka_time = FLACTime()
        for f in sorted(self.source):
            if self.GetOutputFilename() in f.replace(ext.FLAC, ext.WAV):
                continue
            tag = mutagen.flac.FLAC(f)
            try:
                track = {"title": tag["TITLE"][0],
                         "track": tag["TRACKNUMBER"][0],
                         "start_time": mka_time.MKACode()}
            except KeyError as key:
                raise TagNotFoundError(f"{f} doesn't contain key {key}")
            tags = {"disc": "DISCNUMBER",
                    "subindex": "SUBINDEX",
                    "subtitle": "SUBTITLE",
                    "side": "SIDE",
                    "phase": "PHASE"}
            for skey, tkey in tags.items():
                with IgnoreKeyError:
                    track[skey] = tag[tkey][0]
            if GetDisc(track) not in self.disc_data:
                with IgnoreKeyError:
                    self.disc_data[GetDisc(track)] = tag["DISC_NAME"][0]
            self.tracks.append(track)
            mka_time += tag.info.length

    def _GetTag(self):
        return mutagen.flac.FLAC(self.source[0])

    def _PrintMetadata(self):
        Metadata._PrintMetadata(self)
        for disc, name in sorted(self.disc_data.items()):
            print(f"Disc {disc} Name: {name}")


class CueMetadata(Metadata):
    """Class holding the metadata information obtained from a CUE sheet file.
    Searches through the CUE sheet to obtain certain tags, though it only
    supports CUE sheets which describe one file.  Multiple files can be handled
    via ``AlbumMetadata`` provided the files are tagged correctly.
    Supported top-level tags:
      FILE, PERFORMER, TITLE
    Support top-level remarks, starting with 'REM':
      DATE, DISC, DISCS, GENRE, ISSUE_DATE, LABEL, VERSION,
      ORIGINAL_MEDIUM, DISC_NAME
    Can either be called directly via ``CueMetadata(cue_sheet_name, args)``
    where args is an optional parameter, but suggested, or via
    ``GetMetadata(cue_sheet_name, args)`` so long as cue_sheet_name is a string
    that ends with '.cue'.

    See the parent class ``Metadata`` for more information.
    """

    @property
    def sumparts(self):
        return True

    def _initialize(self, args):
        with open(self.source) as cue:
            lines = cue.readlines()
        for i, line in enumerate(lines):
            if line.startswith("FILE"):
                self.filename = CueMetadata.ExtractFilename(line).replace(ext.WAV, ext.FLAC)
            elif line.startswith("REM DISCS"):
                # This needs to come before 'REM DISC' otherwise it would be
                # captured by 'REM DISC' instead.  Also it's not stored in the
                # dictionary component of ``self``.
                self.discs = int(CueMetadata.ExtractProperty(line, "REM DISCS"))
            elif line.startswith("  TRACK"):
                self.tracks.append(CueMetadata.ExtractTrackInformation(lines[i:]))
            elif not line.startswith(" "):  # Search for additional top-level tags
                remarks = ["GENRE", "ISSUE_DATE", "LABEL", "VERSION", "ORIGINAL_MEDIUM", "DISC_NAME"]
                remarks = {f"REM {t}": t for t in remarks}
                # Note that ``"REM DISC "`` has a space at the end because ``"REM DISCID"``
                # is commonly added by CD ripping programs and this is not what we want
                direct_tags = {"REM DATE": "DATE_RECORDED",
                               "REM DISC ": "PART_NUMBER",
                               "PERFORMER": "ARTIST",
                               "TITLE": "TITLE"}
                direct_tags.update(remarks)
                for key, tag in direct_tags.items():
                    if line.startswith(key):
                        self[tag] = CueMetadata.ExtractProperty(line, key)
                        break

        # Pull missing information from source audio:
        tags = self._GetTag()
        for tag in ["TITLE", "ARTIST", "GENRE"]:
            if self[tag] is None and tag in tags:
                self[tag] = tags[tag][0]
        if self["DATE_RECORDED"] is None and "DATE" in tags:
            self["DATE_RECORDED"] = tags["DATE"][0]

    def _GetTag(self):
        directory = os.path.dirname(self.source)
        filename = os.path.join(directory, self.filename)
        return mutagen.flac.FLAC(filename)

    @staticmethod
    def ExtractProperty(line, name):
        """Helper method to deal with lines in a CUE sheet which
        have the form:
            name "value"
        where ``name`` may have whitespace inside it, before it, and
        the quote marks are optional with possible whitespace at the
        end of the line.  The return value would be ``value``.

        Expects ``str`` input and output."""
        line = line.replace('"', '')
        line = line.replace(name, '')
        return line.strip()

    @staticmethod
    def ExtractTrackInformation(lines):
        """Get all the data about this track
        The lines variable holds the entire CUE sheet's lines
        index points to the element in the list which starts with
        '  TRACK' and we want to continue to get data about this track
        so long as our lines start with 4 spaces
        """

        # The starting line should be something like '  TRACK 01 AUDIO'
        # and we want to create ``data = {'track': '1'}``
        # NB: Cue format has a 99 track limit
        data = {"track": CueMetadata.ExtractProperty(lines[0], "TRACK")[0:2].lstrip("0")}

        # Parse the remaining lines for this track to find the track starting time
        # which is typically, but not necessarily, a line starting with '    INDEX 01'
        # Also want to pick up any extra tags in the block and store it in ``data``,
        # eg, the 'TITLE' field.  Since not all fields are valid but remarks are
        # it's necessary to "un-remark" the lines starting with 'REM '
        times = {}
        for line in lines[1:]:
            if not line.startswith(' ' * 4):
                break
            line = line.strip()
            # Don't consider multi-artist albums
            if line.startswith("PERFORMER"):
                continue
            line = line.replace("INDEX ", "INDEX")  # Turn 'INDEX 01' into 'INDEX01', etc.
            line = line.replace("REM ", "")  # Make remarks appear as valid tags
            name = line.split(" ")[0]
            info = CueMetadata.ExtractProperty(line, name)
            if not info:
                continue
            name = name.lower()
            if "INDEX" in line:
                # Handle these time codes separately since there may be more than one
                times[name] = time.CueTimeToMKATime(info)
            else:
                data[name] = info
        # In CUE files, 'INDEX 00' is (typically) used for pre-gap and 'INDEX 01' denotes
        # the start of the actual track.  Higher indices are possible, but rarely used,
        # typically for access to portions of songs.  Here we want to prefer 'INDEX 01'
        # and use 'INDEX 00' if there is no 'INDEX 01' while ignoring higher indices.
        for idx in ["index01", "index00"]:
            if idx in times:
                time_code = idx
                break
        else:
            raise CueFormatError(f"No valid time codes found for track {data['track']}")
        data["start_time"] = times[time_code]
        return data

    @staticmethod
    def ExtractFilename(line):
        """Expects ``line`` to be a string of the form:
          FILE "Some filename.[wav|flac]" WAVE
        Uses the ``ExtractProperty`` method to convert this to
          Some filename.[wav|flac] WAVE
        and then removes the part after the extension.
        """
        if not line.startswith("FILE"):
            raise RuntimeError("Can't extract filename from line not starting with 'FILE'")
        line = CueMetadata.ExtractProperty(line, "FILE")
        line = line.split(" ")[:-1]  # Removes trailing 'WAVE' or 'FLAC'
        return " ".join(line)


def GetMetadata(source, args=None):
    """Convenience function to obtain the correct subclass of ``Metadata``.
    Accepts either a ``list[str]`` where every element ends with '.flac' and
    refers to a file, or a ``str`` which ends in '.cue' and refers to a file.
    Another valid input is an object of a class derived from ``Metadata``.
    """
    if issubclass(source.__class__, Metadata):
        return source
    if not args:
        args = arguments.ParseArguments()
    if isinstance(source, str) and source.lower().endswith(ext.CUE) and os.path.isfile(source):
        return CueMetadata(source, args)
    if isinstance(source, list):
        if any(not os.path.isfile(f) or not f.lower().endswith(ext.FLAC) for f in source):
            raise ValueError("List input supported but must be list of FLAC file name")
        cls = MultidiscMetadata if args.multidisc else AlbumMetadata
        return cls(source, args)
    raise TypeError("Only supported inputs are Metadata objects, list of FLAC file names, or .CUE filename")
