import os
import re

import mutagen.flac

from tools.flac import metadata
from tools.flac.arguments import ParseArguments
from tools.util import ext
from tools.util.flacutil import DirectoryName, FileName, GetFilenames


def DiscTag(data):
    '''Extracts the disc number and formats it according to the number
    of discs in the set, ie, 2 digits if there are 10 or more discs and 1
    digit if there are fewer than 10 discs.  Input parameter ``data`` is
    expected to be a ``mutagen.flac.FLAC`` or ``mutagen.flac.VCFLACDict``,
    however any ``dict``-like interface should work.  The values returned
    from this interface should be a ``list[str]``, or compatible, with the
    actual data stored at index 0.  If the keys "DISCTOTAL" or "DISCNUMBER"
    are not both present, the empty string is returned.'''
    if any(x not in data for x in ["DISCTOTAL", "DISCNUMBER"]):
        return ""
    get = lambda key: data[key][0]
    if int(get("DISCTOTAL")) < 2:
        raise RuntimeError("Needs multiple discs")
    # str(int(x)) such that if x == "01", str(int(x)) == "1", for 2-9 disc sets
    # str(int(x)) such that if x == "1", str(int(x)) == "01" for 10-99 disc sets
    get = lambda key: str(int(data[key][0]))
    disclen = len(get("DISCTOTAL"))
    discnum = get("DISCNUMBER").zfill(disclen)
    return "{}.".format(discnum)

def NewName(f, mdata):
    data = mutagen.flac.FLAC(f)
    pattern = "{artist} - {disc}{track} - {title}.flac"
    try:
        track = data["TRACKNUMBER"][0].zfill(2)
        name = pattern.format(artist=mdata["ARTIST"],
                              disc=DiscTag(data),
                              track=track,
                              title=data["TITLE"][0])
    except KeyError as key:
        print("{} has no value for {}".format(f, key))
        name = f
    name = re.compile("[<>:/\\\\]").sub("-", name)
    name = re.compile("[|?*]").sub("", name)
    name = name.replace('"', "'")
    return os.path.join(DirectoryName(f), name)

def PrintTopBorder(width):
    print("/{}\\".format("-" * (width + 6)))

def PrintBottomBorder(width):
    print("\\{}/".format("-" * (width + 6)))

def PrintDivider(width):
    print("|{}|".format("-" * (width + 6)))

def PrintTitle(title, width):
    print("|{}|".format(title.center(width + 6)))

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
            print("| {} => {} |".format(FileName(f[0]).ljust(length), FileName(f[1]).ljust(outlength)))
        except UnicodeEncodeError:
            print("-- Unicode problems --")
    PrintBottomBorder(length + outlength)
    if input("Perform renaming? ").lower().startswith("y"):
        for f in zip(files, outfiles):
            os.rename(*f)

if __name__ == '__main__':
    main()
