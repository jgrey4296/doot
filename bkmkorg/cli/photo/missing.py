"""
Script to find missing photos

"""
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
from hashlib import sha256
from shutil import copy

import pathlib as pl
from bkmkorg.bibtex import parsing as BU
from bkmkorg.files import hash_check
from bkmkorg.files import collect
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Find and Hash images, revealing duplicates"]))
parser.add_argument('-l', '--library', action="append", required=True)
parser.add_argument('-t', '--target', action="append", required=True)
parser.add_argument('-c', '--copy', action="store_true")
parser.add_argument('-o', '--output', required=True)
##-- end argparse

##-- ifmain
if __name__ == "__main__":
    logging.info("Starting Photo Description")

    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    args.target = pl.Path(args.target).expanduser().resolve()

    logging.info("Finding library images")
    library_images = collect.get_data_files(args.library, collect.img_and_video)
    logging.info("Finding target images")
    target_images = collect.get_data_files(args.target, collect.img_and_video)
    logging.info("Finding missing images")
    missing = hash_check.find_missing(library_images, target_images)
    logging.info("Found %s missing images", len(missing))

    #write conflicts to an org file:
    if not args.copy:
        assert(args.output.is_file())
        assert(args.output.suffix == ".org")
        count = 0
        grouping = int(len(missing) / 100)
        with open(args.output, 'w') as f:
            f.write("* Missing\n")
            for i,x in enumerate(missing):
                if (i % grouping) == 0:
                    f.write("** Group {}\n".format(count))
                    count += 1

                f.write("   [[{}]]\n".format(x))


    # create a directory and copy files missing from the library in
    elif args.copy:
        assert(args.target.is_dir())
        if not args.target.exists():
            args.target.mkdir()

        for x in missing:
            path   = x.name
            copy_dir = args.target / x.parts[-2]

            if not copy_dir.exists():
                copy_dir.mkdir()
            copy(x, copy_dir)

##-- end ifmain
