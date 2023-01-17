#/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import argparse
import json
import logging as logmod
import pathlib
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

from bkmkorg.files.hash_check import map_files_to_hash

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

##-- argparse
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Check files are valid"]))
parser.add_argument('--target', required=True)
parser.add_argument('--output', required=True)
##-- end argparse

def main():

    ##-- Logging
    DISPLAY_LEVEL = logmod.WARN
    LOG_FILE_NAME = "log.{}".format(pathlib.Path(__file__).stem)
    LOG_FORMAT    = "%(asctime)s | %(levelname)8s | %(message)s"
    FILE_MODE     = "w"
    STREAM_TARGET = stderr # or stdout

    logging         = logmod.root
    logging.setLevel(logmod.NOTSET)
    console_handler = logmod.StreamHandler(STREAM_TARGET)
    file_handler    = logmod.FileHandler(LOG_FILE_NAME, mode=FILE_MODE)

    console_handler.setLevel(DISPLAY_LEVEL)
    # console_handler.setFormatter(logmod.Formatter(LOG_FORMAT))
    file_handler.setLevel(logmod.DEBUG)
    # file_handler.setFormatter(logmod.Formatter(LOG_FORMAT))

    logging.addHandler(console_handler)
    logging.addHandler(file_handler)
    ##-- end Logging

    args = parser.parse_args()
    args.target = pl.Path(args.target).expanduser().resolve()
    args.output = pl.Path(args.output).expanduser().resolve()
    assert(args.output.is_dir())

    logging.info("Checking Validity in %s", args.target)
    logging.info("Outputting to %s", args.output)

    existing_hash_dict = {}

    if (args.output / "hashes.json").exists():
        logging.info("Existing Hashes Found")
        with open(args.output / "hashes.json", 'r') as f:
            existing_hash_dict = json.load(f)

    found = collect.get_data_files(args.target, [".pdf", ".epub"])

    logging.info("Hashing %s", len(found))

    new_hash_dict = map_files_to_hash(found)

    # Get differences
    differences = []
    missing     = []
    logging.info("Calculating differences")
    for val in new_hash_dict.keys():
        if val not in existing_hash_dict:
            missing.append(val)
            continue

        if existing_hash_dict[val] != new_hash_dict[val]:
            differences.append(val)

    # Write out again
    logging.info("Writing Output")
    with open(args.output / "hashes.json", 'w') as f:
        json.dump(new_hash_dict,
                  f,
                  indent=4,
                  sort_keys=True)

    with open(args.output / "differences", 'a') as f:
        f.write("\n".join(differences))

    with open(args.output / "missing", 'a') as f:
        f.write("\n".join(missing))


##-- ifmain
if __name__ == '__main__':
    main()

##-- end ifmain
