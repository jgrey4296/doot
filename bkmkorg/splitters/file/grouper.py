"""
Grouper script to put a mass of files in subdirectories
"""
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
import pathlib as pl
from math import floor
from subprocess import call
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.grouper"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Take a subdirectory of files, group into subdirectories of size g"]))
parser.add_argument('-t', '--target', default="~/twitterthreads")
parser.add_argument('-g', '--groupnum',  default=5)
parser.add_argument('-p', '--preface', default="grouped")
##-- end argparse


if __name__ == "__main__":
    args = parser.parse_args()
    args.target = pl.Path(args.target).expanduser().resolve()

    all_files = args.target.iterdir()
    only_orgs = [x for x in all_files if x.suffix == '.org']

    # group orgs into len/ratio groups
    groups = [[] for x in range(args.groupnum)]
    num_per_group =  floor(len(only_orgs) / args.groupnum)

    count = 0
    current_group = 0
    for i,x in enumerate(only_orgs):
        groups[current_group].append(x)
        count += 1
        if current_group < args.groupnum-1 and count >= num_per_group:
            count = 0
            current_group += 1

    # create group names
    group_names = [f"{args.preface}_{x}" for x in range(args.groupnum)]

    logging.info("Group Names: %s", ", ".join(group_names))

    # check no group name already exists
    assert(all([not (args.target / x).exists() for x in group_names]))


    # create the groups
    [(args.target / x).mkdir() for x in group_names]
    logging.info("Expanded location: %s", args.target)

    # move the org files and their associated files into the
    # appropriate group
    for gname, group in zip(group_names, groups):
        for ofile in group:
            original  = ofile
            file_dir = ofile.parent / f"{original.stem}_files"
            group_dir = args.target / gname
            call(['mv',
                  str(original),
                  str(group_dir)])
            logging.info("Moving: %s", ofile)
            logging.info("Moving: %s", file_dir)
            call(['mv',
                  str(file_dir)),
                  str(group_dir)])
