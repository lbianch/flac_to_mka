#!/usr/bin/env python
import os
import logging
import atexit
from tools.flac import arguments, merger, verifier, metadata, cuewriter
from tools.mka import arthandler, chapterwriter, createmka, tagwriter
from tools.util import ext, flacutil, namegen
logging = logging.getLogger(__name__)


def flac_exists(flacname, mergeflacs):
    if os.path.exists(flacname):
        if mergeflacs:
            os.unlink(flacname)
        return True
    if not mergeflacs:
        msg = "Requested skip merge mode but file '{}' doesn't exist"
        raise FileNotFoundError(msg.format(flacname))
    return False


def MakeCueOrFlac(args, files, mdata, filename):
    # Produce CUE sheet and unregister cleanup to preserve it
    if not args.no_confirm and not mdata.Confirm():
        return
    cuewriter.CueSheet(files, mdata).Create(filename(ext.CUE))
    atexit.unregister(cuewriter.CueSheet.Clean)
    if args.cueflac:
        # Also merge the flac and unregister cleanup
        merger.FLACMerger(files).Create(filename(ext.FLAC))
        atexit.unregister(merger.FLACMerger.Clean)


def MakeMatroska(args, files, mdata, filename):
    artwork = arthandler.Artwork(args, mdata, filename(ext.JPG))
    if not args.no_confirm and not mdata.Confirm():
        return
    # Produce CUE sheet (CD only), tags, chapters
    if not args.multidisc and verifier.FLACVerifier(files[0]).IsCD():
        cuewriter.CueSheet(files, mdata).Create(filename(ext.CUE))
    tagwriter.CreateMatroskaTagger(args, mdata).Create(filename(ext.XML))
    chapterwriter.MatroskaChapters(mdata).Create(filename(ext.CHAPTERS))
    # Perform merging of FLAC files
    if not args.skipmerge:
        # Mode for producing only MKA, therefore skip FLAC merging
        # Really, if we're skipping FLAC Merging then we probably wanted
        # to use CUE file MKA creation mode and shouldn't be in this function
        merger.FLACMerger(files).Create(filename(ext.FLAC))
    createmka.MKACreator(args, mdata, filename, artwork).Create()


def main():
    # Whether we're producing CUE+FLAC or MKA, there are a few
    # common actions we need to do to begin.  These are to process
    # the command line arguments, grab the FLAC files, prepare the
    # metadata, and generate the ``namegen.FileName`` object.  We
    # also want to verify the FLAC files are all of the same
    # specification.
    args = arguments.ParseArguments()
    if args.directory == ".":
        args.directory = os.getcwd()
    files = flacutil.GetFilenames(ext.FLAC, args.directory)
    if not files:
        raise FileNotFoundError("No FLAC files")
    mdata = metadata.GetMetadata(files, args)
    filename = namegen.FileName(mdata.GetOutputFilename(args.directory))
    # If the FLAC files were already merged then we want to remove the
    # output from the ``files`` list, but also delete the output unless
    # we are in MKA-only mode which skips FLAC merging
    if flac_exists(filename(ext.FLAC), not args.skipmerge):
        files.remove(filename(ext.FLAC))
    verifier.FLACVerifier(files)
    # From here, the two outputs differ so we hand off to the appropriate
    # function depending on the command line argument.
    func = MakeCueOrFlac if (args.cue or args.cueflac) else MakeMatroska
    func(args, files, mdata, filename)


if __name__ == '__main__':
    main()
