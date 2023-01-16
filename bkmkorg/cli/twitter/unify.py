#!/usr/bin/env python
"""
Integrates newly parsed twitter->org files
into the existing set
"""
##-- imports
from __future__ import annotations

from os import system
import pathlib as pl
import argparse
import datetime
import logging as root_logger
from random import choice
from subprocess import run
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.bibtex import parsing as BU
from bkmkorg.twitter.extraction import get_all_tweet_ids
from bkmkorg.twitter import unify
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
                                    epilog = "\n".join(["Integrate newly parsed twitter orgs into the existing library"]))
parser.add_argument('-s', '--source', action="append", required=True)
parser.add_argument('-l', '--library', action="append", required=True)
parser.add_argument('-e', '--exclude', action="append")
parser.add_argument('-r', '--record')
##-- end argparse

##-- constants
PROCESSED = "_processed"
##-- end constants

def main():
    # Setup
    args         = parser.parse_args()
    args.source  = [pl.Path(x).expanduser().resolve() for x in args.source]
    args.library = [pl.Path(x).expanduser().resolve() for x in args.library]
    if args.exclude is None:
        args.exclude = []

    args.exclude = [pl.Path(x).expanduser().resolve() for x in args.exclude]

    if not args.record:
        args.record = args.library[0] / "update_record"

    logging.info("Update Record: %s", args.record)
    assert(args.record.exists())
    if any([not x.exists() for x in args.source + args.library]):
        raise Exception('Source and Output need to exist')

    #load the newly parsed org names
    # { file_name : full_path }
    newly_parsed = sorted(collect.get_data_files(args.source, ext=".org"))

    logging.info("Newly parsed to transfer: %s", len(newly_parsed))

    #get the existing org names, as a dict with its location
    library_orgs = collect.get_data_files(args.library, ext=".org")
    existing_orgs = {}
    for lib_org in library_orgs:
        if lib_org in args.exclude:
            continue

        existing_orgs[lib_org.name] = lib_org.parent

    logging.info("Existing orgs: %s", len(existing_orgs))

    totally_new = []
    #now update existing with the new

    for x in newly_parsed:
        if x.name not in existing_orgs:
            logging.info("Found a completely new user: %s", x)
            totally_new.append(x)
            continue

        unify.integrate(x, existing_orgs)

    logging.info("Completely new to transfer: %s", len(totally_new))

    # Now copy completely new files
    for x in sorted(totally_new):
        unify.copy_new(x, args.library[0])

    unify.update_record(args.record, args.source)
    system('say -v Moira -r 50 "Finished Integrating"')

##-- ifmain
if __name__ == "__main__":
    main()

##-- end ifmain
