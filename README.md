# FLAC to Matroska Audio Converter


## Using Matroska Audio with foobar2000:

Though Matroska is a widely supported container, it is generally used for video rather than audio-only.  The best player I have found for Matroska Audio files is foobar2000, which offers excellent support for Matroska Audio files.  Most video player software can recognize the tracks in Matroska Audio files, but only once playback begins.  Most importantly, foobar2000 can easily edit Matroska audio tags removing the need to re-produce the Matroska audio file simply because the metadata is incorrect.

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
