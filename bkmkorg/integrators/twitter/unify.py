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

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.twitter.extraction import get_all_tweet_ids
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

def copy_files(source_dir:pl.Path, target_dir:pl.Path):
    logging.info("Copying from %s to %s", source_dir, target_dir)
    if source_dir.exists() and not target_dir.exists():
        logging.info("as group")
        result = run(['cp' ,'-r', str(source_dir), str(target_dir)], capture_output=True, check=True)
    elif target_dir.exists():
        logging.info("as individual")
        for y in source_dir.iterdir():
            if not y.is_file():
                continue

            call_sig = ['cp', str(y), str(target_dir / y.name)]
            run(call_sig, capture_output=True, check=True)


def copy_new(source:pl.Path, lib_path:pl.Path):
    logging.info("Adding to library with: %s", source)
    file_dir  = source.parent / f"{source.stem}_files"

    first_letter = source.name[0].lower()
    if not ("a" <= first_letter <= "z"):
        first_letter = "symbols"

    target_for_new = lib_path / f"group_{first_letter}"

    if not (target_for_new / source.name).exists():
        run(['cp', str(source), str(target_for_new)], capture_output=True, check=True)

    run(["mv", str(source), str(source.parent / f"{source.name}{PROCESSED}")], capture_output=True, check=True)

    copy_files(file_dir, target_for_new / f"{source.stem}_files")


def integrate(source:pl.Path, lib_dict:dict[str,Any]):
    logging.info("Integrating: %s", source)
    new_files      = source.parent / f"{source.stem}_files"
    existing_org   = lib_dict[source.name] /  source.name
    existing_files = lib_dict[source.name] / f"{source.stem}_files"

    assert(existing_org.exists())
    if not existing_files.exists():
        existing_files.mkdir()

    with open(source, 'r') as f:
        lines = f.read()

    with open(existing_org, 'a') as f:
        f.write("\n")
        f.write(lines)

    run(["mv", str(source), str(source.parent / f"{source.name}{PROCESSED}")], capture_output=True, check=True)

    if not new_files.exists():
        return

    copy_files(new_files, existing_files)



def update_record(path:pl.Path, sources:List[pl.Path]):
    now : str = datetime.datetime.now().strftime("%Y-%m-%d")

    all_ids = get_all_tweet_ids(*sources, ext=".org_processed")

    # add it to the library record
    with open(path, 'a') as f:
        # Insert date
        f.write(f"{now}:\n\t")
        f.write("\n\t".join(sorted(all_ids)))
        f.write("\n----------------------------------------\n")


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
    newly_parsed = sorted(retrieval.get_data_files(args.source, ext=".org"))

    logging.info("Newly parsed to transfer: %s", len(newly_parsed))

    #get the existing org names, as a dict with its location
    library_orgs = retrieval.get_data_files(args.library, ext=".org")
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

        integrate(x, existing_orgs)

    logging.info("Completely new to transfer: %s", len(totally_new))

    # Now copy completely new files
    for x in sorted(totally_new):
        copy_new(x, args.library[0])

    update_record(args.record, args.source)
    system('say -v Moira -r 50 "Finished Integrating"')

if __name__ == "__main__":
    main()
