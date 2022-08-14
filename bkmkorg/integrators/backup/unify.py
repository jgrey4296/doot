#!/opt/anaconda3/envs/bookmark/bin/python
"""
Verify a backup of a library is up to date

"""
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
import pathlib as pl
from filecmp import dircmp
from shutil import copy, copytree
import warnings

from bkmkorg.utils.dfs.pathcmp import PathCmp
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Pathb(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join([""]))
parser.add_argument('--library', required=True)
parser.add_argument('--target', required=True)
parser.add_argument('-e', '--exclude', action="append")
##-- end argparse

warnings.warn("This is broken till i factor out dircmp")

def copy_missing(the_cmp, exclude=None):
    if exclude is None:
        exclude = []
    queue = [the_cmp]

    while bool(queue):
        current = queue.pop(0)
        # Copy left_only to right
        for missing in current.left_only:
            loc_l =  missing
            loc_r = current.right / missing.name
            if loc_l.is_file() and missing.suffix not in exclude):
                logging.info("Missing: library -> %s -> target : %s : %s", missing, loc_l, loc_r)
                copy(str(loc_l), str(loc_r))
            elif isdir(loc_l):
                logging.info("Missing: library -> %s -> target : %s : %s", missing, loc_l, loc_r)
                copytree(str(loc_l), str(loc_r))

        queue += current.subdirs.values()

def main():
    args         = parser.parse_args()
    args.library = pl.Path(args.library).expanduser().resolve()
    args.target  = pl.Path(args.target).expanduser().resolve()

    the_cmp = PathCmp(args.library, args.target)

    copy_missing(the_cmp, exclude=args.exclude)


if __name__ == "__main__":

    main()
