# FLAC to Matroska Audio Converter

## Setup

## Usage

### Modes
The program supports two kinds of input, FLAC + CUE or a directory with FLAC files.  For a directory with multiple FLAC + CUE files, an explicit CUE filename may be given.  

When the input files are CD specification (44.1kHz, 16-bit, 2 channels), a CUE file is either created or a new CUE file is created from the original, and attached to the Matroska Audio output.  This makes it simple to write to a CD as one only needs to extract the CUE file and the FLAC audio track from the Matroska Audio to recover FLAC + CUE.  Note that when a directory of FLAC files in the CD format is used, the CUE file is generated automatically.  CUE file generation is skipped for audio files which use another sample rate, bit-depth, or which are not stereo as they are not writable to CD.

For a directory with FLAC files, an optional ``--multidisc`` parameter may be passed.  In this mode, a directory which contains files from multiple discs becomes merged into a single file.  In this mode, a CUE file is not created as such output is not writable to CD.

### Artwork
This program requires artwork to be present for each Matroska Audio file.  With an input directory, the directory is searched for JPG, JPEG, and PNG files.  If multiple files are found, the highest resolution image is used.  Only images which are roughly square (aspect ratio between 0.99 and 1.01) can be automatically used.  If no artwork is found in the directory, then the (first) FLAC file is checked for embedded artwork, requiring the same roughly square aspect ratio.

If the only artwork found is under 500 pixels wide then production will abort.  If that artwork truly is wanted, then the `--image` parameter may be used to force the artwork to be used, which also bypasses the aspect ratio requirement.

### Supported Tags
Supported collection-level FLAC tags:

 * ARTIST
 * ALBUM 
 * DATE
 * GENRE
 * DISCTOTAL
 * LABEL
 * ISSUE_DATE
 * ORIGINAL_MEDIUM
 * VERSION

Supported disc-level FLAC tags

 * DISC_NAME

Supported track-level FLAC tags

 * TITLE
 * DISCNUMBER 
 * TRACKNUMBER
 * SIDE
 * PHASE
 * SUBINDEX
 * SUBTITLE  
      
### Limitations
Only one album artwork is supported.

Tags that aren't one of the above listed tags are not copied.  This is intentional as many audio ripping programs add a `Comment` field with the program's name, a ripping date, or similar information which is not desired.  One possible extension would be to allow attachment of a ripping program generate log file if such information is desired.

## Using Matroska Audio with foobar2000:

Though Matroska is a widely supported container, it is generally used for video rather than audio-only.  The best player I have found for Matroska Audio files is foobar2000, which offers excellent support for Matroska Audio files.  Most video player software can recognize the tracks in Matroska Audio files, but only once playback begins.  Most importantly, foobar2000 can easily edit Matroska audio tags removing the need to re-produce the Matroska audio file simply because the metadata is incorrect.

Another very useful feature of foobar2000 is the ability to convert files to lossy formats for use on, eg, a smartphone.  

Below are some foobar2000 snippets designed to operate with the metadata tags used by this project.

Grouping scheme:
```
%artist% - %album%[ : %disc_name%][ '('%version%')'] '['%codec% %samplerate%Hz[ %__bitspersample%-bit] %channels%']'
```

Track number column:
```
[%disc%.][%side%.]%tracknumber%[:%subindex%]
```

Library view by artist/label:
 ```
%artist%|[%date% - ]%album%$if(%label%,|[$if3(%issue_date%,%date%) - ]%label% ['('%version%')' ]'['[%hd_format% ][%original_medium% ]%codec%']',[|%version%])$if(%disc_name%,|[Disc %disc% - ]%disc_name%,)|[%disc%.][%side%.][%phase%.]%tracknumber%[.%subindex%]. [Phase %phase%: ]%title%[: %subtitle%]
```

Example view:
```
Artist
 + Date - Album
   + Issue Date - Label (Version) [Sample Rate/Bit Depth Channels Medium Codec]
     + Disc Number - Disc Name
       + Disc Number.Side.Phase.TrackNumber.Subindex. Phase Title: Subtitle
```
The second row only displays if Label is set; if Label is not set but Version is then it reduces to `Version`.  The 3rd row only displays if Disc Name is set.  For a typical CD converted to FLAC + CUE then converted to MKA without label/version/disc name fields, this is simply
```
Artist
  + Date - Album
    + DiscNumber.TrackNumber Title
```
For a 2 CD release with separate disc names, a label, and issue date:
```
Artist
  + Date - Album
    + Issue Date - Label [44.1kHz/16 CD FLAC]
      + Disc 1 - Disc 1 Name
        + 1.01 - Track 1 
        ...
      + Disc 2 - Disc 2 Name
        + 2.01 - Track 1
```
