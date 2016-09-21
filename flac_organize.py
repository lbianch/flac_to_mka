#!/usr/bin/env python3
import os
import mutagen.flac
from tools.flac.arguments import ParseArguments
from tools.util.flacutil import DirectoryName, FileName, GetFilenames


def disc_tag(data):
    try:
        if int(data["DISCTOTAL"][0]) < 2:
            raise RuntimeError("Needs multiple discs")
        disclen = len(str(int(data["DISCTOTAL"][0])))
        discnum = str(int(data["DISCNUMBER"][0])).zfill(disclen)
        return "{}.".format(discnum)
    except KeyError:
        return ""


def new_name(in_file):
    data = mutagen.flac.FLAC(in_file)
    pattern = "{} - {}{} - {}.flac"
    try:
        track = data["TRACKNUMBER"][0].zfill(2)
        name = pattern.format(data["ARTIST"][0], disc_tag(data), track, data["TITLE"][0])
        if not os.path.exists(data["ALBUM"][0]):
            os.mkdir(data["ALBUM"][0])
        return os.path.join(DirectoryName(in_file), data["ALBUM"][0], name)
    except KeyError as key:
        print("{} has no value for {}".format(in_file, key))
        return in_file


def print_top_border(width):
    print("/{}\\".format("-" * (width + 6)))


def print_bottom_border(width):
    print("\\{}/".format("-" * (width + 6)))


def print_divider(width):
    print("|{}|".format("-" * (width + 6)))


def print_title(title, width):
    print("|{}|".format(title.center(width + 6)))


def main():
    args = ParseArguments()
    files = GetFilenames(".flac", args.directory)
    os.chdir(args.directory)
    outfiles = [new_name(f) for f in files]
    length = max(len(FileName(f)) for f in files)
    outlength = max(len(FileName(f)) for f in outfiles)
    print_top_border(length + outlength)
    print_title(DirectoryName(args.directory), length+outlength)
    print_divider(length + outlength)
    for f_name in zip(files, outfiles):
        try:
            msg = "| {} => {} |"
            args = [FileName(val[0]).ljust(val[1]) for val in zip(f_name, [length, outlength])]
            print(msg.format(*args))
        except UnicodeEncodeError:
            print("-- Unicode problems --")
    print_bottom_border(length + outlength)
    if input("Perform renaming? ").lower().startswith("y"):
        for f_name in zip(files, outfiles):
            os.rename(*f_name)

if __name__ == '__main__':
    main()
