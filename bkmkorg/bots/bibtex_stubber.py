#!/usr/bin/env python3
from __future__ import annotations

import abc
import argparse
import logging as logmod
from datetime import datetime
from configparser import ConfigParser
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from re import Pattern
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref
from string import Template


logging = logmod.getLogger(__name__)

if TYPE_CHECKING:
    # tc only imports
    pass

from bkmkorg.utils.dfs.files import get_data_files
from bkmkorg.utils.bibtex.writer import JGBibTexWriter

DISPLAY_LEVEL = logmod.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
LOG_FORMAT    = "%(asctime)s | %(levelname)8s | %(message)s"
FILE_MODE     = "w"
STREAM_TARGET = stderr # or stdout

logger          = logmod.getLogger(__name__)
console_handler = logmod.StreamHandler(STREAM_TARGET)
file_handler    = logmod.FileHandler(LOG_FILE_NAME, mode=FILE_MODE)

console_handler.setLevel(DISPLAY_LEVEL)
# console_handler.setFormatter(logmod.Formatter(LOG_FORMAT))
file_handler.setLevel(logmod.DEBUG)
# file_handler.setFormatter(logmod.Formatter(LOG_FORMAT))

logger.addHandler(console_handler)
logger.addHandler(file_handler)
logging = logger
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Create Bibtex Stubs for pdfs and epubs"]))
parser.add_argument('--source', default=None)
parser.add_argument('--target', default=None)
parser.add_argument('--config', default="/Volumes/documents/github/py_bookmark_organiser/bots.config")

args = parser.parse_args()

expander = lambda x: abspath(expanduser(x))

config   = ConfigParser(allow_no_value=True, delimiters='=')
config.read(expander(args.config))

target_dir = expander(args.source or config['BIBTEX']['stub_source'])
stub_file  = expander(args.target or config['BIBTEX']['stub_target'])
exts       = config['BIBTEX']['stub_exts'].split(" ")

stub_t     = Template("@misc{stub_$id,\n  author = {},\n  title = {$title},\n  year = {$year},\n  file = {$file}\n}")

def main():
    year = datetime.now().year

    # Get the files from source
    to_stub = get_data_files(target_dir, ext=exts)
    # Remove already stubbed files
    with open(stub_file, 'r') as f:
        stub_str = f.read()

    to_stub_filtered = [x for x in to_stub if x not in stub_str]
    print(f"Adding {len(to_stub_filtered)} stubs")
    if not bool(to_stub_filtered):
        exit()

    # Gen Stubs
    stub_str = "\n\n".join([stub_t.substitute(id=num,
                                              title=splitext(split(f)[1])[0],
                                              year=year, file=f)
                            for num, f in enumerate(sorted(to_stub_filtered, key=lambda x: split(x)[1]))])

    # Write into target
    with open(stub_file, 'a') as f:
        f.write("\n")
        f.write(stub_str)



if __name__ == '__main__':
    main()
