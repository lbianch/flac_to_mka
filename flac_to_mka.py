#!/usr/bin/env python
import logging

from flac_to_mka import cue, multiflac
from flac_to_mka.flac.arguments import ParseArguments
from flac_to_mka.util.flacutil import GetFilenames
from flac_to_mka.util import ext


args = ParseArguments()
logging.basicConfig(level=args.logging_level,
                    format='[%(name)s - %(asctime)s] %(levelname)s: %(message)s')


def main():
    # Check for explicit .cue as input:
    if args.directory.lower().endswith(ext.CUE):
        cue.main()
        return
    flacs = GetFilenames(ext.FLAC, args.directory)
    cues = GetFilenames(ext.CUE, args.directory)
    if not flacs:
        raise FileNotFoundError("No FLAC file(s)")
    if len(flacs) == 1 and len(cues) == 1:
        cue.main()
    else:
        multiflac.main()


if __name__ == '__main__':
    main()
