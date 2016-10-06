# flac_to_mka

Grouping scheme:
%artist% - %album%[ : %disc_name%][ '('%version%')'] '['%codec% %samplerate%Hz[ %__bitspersample%-bit] %channels%']'

Track number column:
[%disc%.][%side%.]%tracknumber%[:%subindex%]

Library view by artist/label:
%artist%|[%date% - ]%album%$if(%label%,|[$if3(%issue_date%,%date%) - ]%label% ['('%version%')' ]'['[%hd_format% ][%original_medium% ]%codec%']',[|%version%])$if(%disc_name%,|[Disc %disc% - ]%disc_name%,)|[%disc%.][%side%.][%phase%.]%tracknumber%[.%subindex%]. [Phase %phase%: ]%title%[: %subtitle%]

