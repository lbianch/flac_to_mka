import os
import re

import mutagen.flac
from flac_to_mka.flac import metadata
from flac_to_mka.flac.arguments import ParseArguments
from flac_to_mka.util.flacutil import DirectoryName, FileName, GetFilenames

from flac_to_mka.util import ext


def DiscTag(data):
    """Extracts the disc number and formats it according to the number
    of discs in the set, ie, 2 digits if there are 10 or more discs and 1
    digit if there are fewer than 10 discs.  Input parameter ``data`` is
    expected to be a ``mutagen.flac.FLAC`` or ``mutagen.flac.VCFLACDict``,
    however any ``dict``-like interface should work.  The values returned
    from this interface should be a ``list[str]``, or compatible, with the
    actual data stored at index 0.  If the keys "DISCTOTAL" or "DISCNUMBER"
    are not both present, the empty string is returned."""
    if any(x not in data for x in ["DISCTOTAL", "DISCNUMBER"]):
        return ""
    if int(data["DISCTOTAL"][0]) < 2:
        raise RuntimeError("Needs multiple discs")

    # str(int(y)) such that if y == "01", str(int(y)) == "1", for 2-9 disc sets
    # str(int(y)) such that if y == "1", str(int(y)) == "01" for 10-99 disc sets
    def get(key):
        return str(int(data[key][0]))
    disclen = len(get("DISCTOTAL"))
    return f"{get('DISCNUMBER').rjust(disclen, '0')}."


def NewName(f, mdata):
    data = mutagen.flac.FLAC(f)
    if 'SUBINDEX' in data:
        pattern = "{artist} - {disc}{track:02}.{subindex:02} - {title} - {subtitle}.flac"
    else:
        pattern = "{artist} - {disc}{track:02} - {title}.flac"
    try:
        metadata = dict(artist=mdata["ARTIST"],
                        disc=DiscTag(data),
                        track=int(data["TRACKNUMBER"][0]),
                        title=data["TITLE"][0])
        if 'SUBINDEX' in data:
            metadata['subindex'] = int(data['SUBINDEX'][0])
            metadata['subtitle'] = data['SUBTITLE'][0]
    except KeyError as key:
        print(f"{f} has no value for {key}")
        name = f
    else:
        name = pattern.format(**metadata)
    name = re.compile(r"[<>:/\\]").sub("-", name)
    name = re.compile("[|?*]").sub("", name)
    name = name.replace('"', "'")
    return os.path.join(DirectoryName(f), name)


def PrintTopBorder(width):
    print(f"/{'-' * (width + 6)}\\")


def PrintBottomBorder(width):
    print(f"\\{'-' * (width + 6)}/")


def PrintDivider(width):
    print(f"|{'-' * (width + 6)}|")


def PrintTitle(title, width):
    print(f"|{title.center(width + 6)}|")


def main():
    args = ParseArguments()
    files = GetFilenames(ext.FLAC, args.directory)
    mdata = metadata.AlbumMetadata(files, args)
    outfiles = [NewName(f, mdata) for f in files]  
    length = max(len(FileName(f)) for f in files)
    outlength = max(len(FileName(f)) for f in outfiles)
    PrintTopBorder(length + outlength)
    PrintTitle(DirectoryName(args.directory), length + outlength)
    PrintDivider(length + outlength)
    for f in zip(files, outfiles):
        try:
            print(f"| {FileName(f[0]).ljust(length)} => {FileName(f[1]).ljust(outlength)} |")
        except UnicodeEncodeError:
            print("-- Unicode problems --")
    PrintBottomBorder(length + outlength)
    if input("Perform renaming? ").lower().startswith("y"):
        for f in zip(files, outfiles):
            os.rename(*f)

if __name__ == '__main__':
    main()
