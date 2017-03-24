import os.path
from logging import getLogger

from flac_to_mka.flac import arguments, cuewriter, metadata
from flac_to_mka.mka import arthandler, chapterwriter, tagwriter, createmka
from flac_to_mka.util import ext, flacutil, namegen


logging = getLogger(__name__)


def main():
    args = arguments.ParseArguments()
    if args.directory == ".":
        args.directory = os.getcwd()
    if os.path.isfile(args.directory):
        filename = args.directory
        args.directory = flacutil.DirectoryName(args.directory)
    else:
        filenames = flacutil.GetFilenames(ext.CUE, args.directory)
        if not filenames:
            raise FileNotFoundError("No CUE file found")
        if len(filenames) > 1:
            raise RuntimeError("Multiple CUE files found")
        filename = filenames[0]
    mdata = metadata.CueMetadata(filename, args)
    basename = namegen.FileName(mdata.GetOutputFilename(args.directory))
    artwork = arthandler.Artwork(args, mdata, basename(ext.JPG))
    if not args.no_confirm and not mdata.Confirm():
        return
    # Now we can actually begin the operation
    cuewriter.CueFilenameChanger(filename, basename(ext.CUE))
    basename[ext.FLAC] = mdata.filename.replace(ext.WAV, ext.FLAC)
    tagwriter.MatroskaTagger(mdata).Create(basename(ext.XML))
    chapterwriter.MatroskaChapters(mdata).Create(basename(ext.CHAPTERS))
    createmka.MKACreator(args, mdata, basename, artwork).Create()

if __name__ == '__main__':
    main()
