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

from bkmkorg.files.pathcmp import PathCmp
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
                                    epilog = "\n".join([""]))
parser.add_argument('--library', required=True)
parser.add_argument('--target', required=True)
##-- end argparse

def dfs_and_copy(lib_root, target_root):
    queue = list(lib_root.iterdir())
    while bool(queue):
        current     = queue.pop()
        rel_current = current.relative_to(lib_root)
        target      = target_root / rel_current
        # logging.info("Checking: %s", rel_current)

        if target.exists() and current.is_dir():
            queue += list(current.iterdir())
            continue
        elif target.exists():
            continue

        assert(not target.exists())
        # TODO check hashes
        if current.is_file():
            logging.info("Missing: library -> target : %s", rel_current)
            copy(str(current), str(target))
        else:
            assert(current.is_dir())
            logging.info("Missing Dir: library -> target : %s %s %s", rel_current, current, target)
            copytree(str(current), str(target))

def main():
    args         = parser.parse_args()
    args.library = pl.Path(args.library).expanduser().resolve()
    args.target  = pl.Path(args.target).expanduser().resolve()

    dfs_and_copy(args.library, args.target)


##-- ifmain
if __name__ == "__main__":

    main()

##-- end ifmain
