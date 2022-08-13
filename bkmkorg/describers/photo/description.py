"""
Photo Description Script
Writes an org file with images that have the same hash
"""
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
from hashlib import sha256

import pathlib as pl
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.file import hash_check
from bkmkorg.utils.dfs import files as retrieval
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

##-- consts
FILE_TYPES = [".gif",".jpg",".jpeg",".png",".mp4",".bmp"]
##-- end consts

##-- argparse
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Find and Hash images, revealing duplicates"]))
parser.add_argument('-t', '--target', action='append', required=True)
parser.add_argument('-o', '--output', required=True)
##-- end argparse


if __name__ == "__main__":
    logging.info("Starting Photo Description")
    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    logging.info("Finding images")
    images = retrieval.get_data_files(args.target, FILE_TYPES)
    logging.info("Hashing {} images".format(len(images)))
    hash_dict, conflicts = hash_check.hash_all(images)
    logging.info("Hashed all images, {} conflicts".format(len(conflicts)))

    #write conflicts to an org file:
    with open(args.output,'w') as f:
        f.write("* Conflicts\n")
        for x in conflicts:
            f.write("** {}\n".format(x))
            f.write("\n".join(["   [[{}]]".format(y) for y in hash_dict[x]]))
