import argparse


def ParseArguments():
    args = argparse.ArgumentParser(prog="FLAC to MKA")
    args.add_argument("directory",
                      help="Directory containing source files")
    args.add_argument("--output",
                      help="Output file name")
    args.add_argument("--image",
                      help="Manually specify cover art file")
    args.add_argument("--forceimage",
                      action="store_true",
                      help="Skip resolution and aspect ratio check of cover art")
    args.add_argument("--genre",
                      help="Manually specify genre")
    args.add_argument("--year",
                      help="Manually specify year (first release)")
    args.add_argument("--artist",
                      help="Manually specify artist")
    args.add_argument("--album",
                      help="Manually specify album")
    args.add_argument("--label",
                      help="Specify the label that issued this release; useful for re-releases")
    args.add_argument("--issuedate",
                      help="Specify the date this version was released; useful for re-releases")
    args.add_argument("--version",
                      help="Specify version of release; useful for regional releases, volumes, or special editions")
    args.add_argument("--medium",
                      help="Specify source medium of release",
                      choices=["CD", "SACD", "DVD", "DVD-A", "Blu-ray",
                               "Web",
                               "Vinyl", "78RPM Vinyl",
                               "LP", "Vinyl LP", "45RPM Vinyl LP",
                               "EP", "Vinyl EP", "45RPM Vinyl EP",
                               "180g Vinyl LP", "180g 45RPM Vinyl LP",
                               "200g Vinyl LP", "200g 45RPM Vinyl LP",
                               "220g Vinyl LP", "220g 45RPM Vinyl LP",
                               "Reel-to-reel", "8-Track", "Cassette", "VHS"])
    args.add_argument("--disc",
                      help="Disc number (must specify number of discs)")
    args.add_argument("--discs",
                      help="Number of discs (must specify disc number)")
    args.add_argument("--no-confirm",
                      action="store_true",
                      help="Don't print metadata before running")
    args.add_argument("--cue",
                      action="store_true",
                      help="Produce only CUE file")
    args.add_argument("--cueflac",
                      action="store_true",
                      help="Produce CUE+FLAC as output instead of MKA")
    args.add_argument("--skipmerge",
                      action="store_true",
                      help="Skip merging of FLAC files, requires file already exists")
    disc_group = args.add_mutually_exclusive_group()
    disc_group.add_argument("--multidisc",
                            action="store_true",
                            help="MKA output should merge multiple discs preserving disc and track numbering")
    disc_group.add_argument("--nodiscs",
                            action="store_true",
                            help="Ignore disc tags; track numbers start at 1 and all tracks are merged")
    return args.parse_args()  # Uses sys.argv
