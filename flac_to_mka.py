#!/usr/bin/env python
import logging
from tools import cue, multiflac
from tools.flac.arguments import ParseArguments
from tools.util import ext
from tools.util.flacutil import GetFilenames

logging.basicConfig(level=logging.INFO,
                    format='[%(name)s - %(asctime)s] %(levelname)s: %(message)s')


def main():
    directory = ParseArguments().directory
    # Check for explicit .cue as input:
    if directory.lower().endswith(ext.CUE):
        cue.main()
        return
    flacs = GetFilenames(ext.FLAC, directory)
    cues = GetFilenames(ext.CUE, directory)
    if not flacs:
        raise FileNotFoundError("No FLAC file(s)")
    if len(flacs) == 1 and len(cues) == 1:
        cue.main()
    else:
        multiflac.main()


if __name__ == '__main__':
    main()
