#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import abc
import argparse
import pathlib as pl
import logging as logmod
from configparser import ConfigParser
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from importlib.resources import files
from re import Pattern, compile
from string import Template
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

from bkmkorg import DEFAULT_BOTS, DEFAULT_CONFIG
from bkmkorg.bibtex.writer import JGBibTexWriter
from bkmkorg.files.collect import get_data_files

##-- end imports

##-- data
data_path = files(f"bkmkorg.{DEFAULT_CONFIG}")
data_bots = data_path.joinpath(DEFAULT_BOTS)
##-- end data

##-- logging
DISPLAY_LEVEL = logmod.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
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
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Create Bibtex Stubs for pdfs and epubs"]))
parser.add_argument('--source', default=None)
parser.add_argument('--target', default=None)
parser.add_argument('--config', default=data_bots)
##-- end argparse

args = parser.parse_args()

config   = ConfigParser(allow_no_value=True, delimiters='=')
config.read(pl.Path(args.config).expanduser().resolve())

target_dir = pl.Path(args.source or config['BIBTEX']['stub_source']).expanduser().resolve()
stub_file  = pl.Path(args.target or config['BIBTEX']['stub_target']).expanduser().resolve()
exts       = config['BIBTEX']['stub_exts'].split(" ")

stub_t     = Template("@misc{stub_$id,\n  author = {},\n  title = {$title},\n  year = {$year},\n  file = {$file}\n}")

exclusion_re = compile(f"^_refiled")

def main():
    year = datetime.now().year

    # Get the files from source
    found = get_data_files(target_dir, ext=exts)
    to_stub = [x for x in found if not exclusion_re.match(x.name)]

    # Remove already stubbed files
    with open(stub_file, 'r') as f:
        stub_str = f.read()

    to_stub_filtered = [x for x in to_stub if x.name not in stub_str]
    print(f"Adding {len(to_stub_filtered)} stubs")
    if not bool(to_stub_filtered):
        exit()

    # Gen Stubs
    stub_str = "\n\n".join([stub_t.substitute(id=num,
                                              title=f.stem,
                                              year=year, file=str(f))
                            for num, f in enumerate(sorted(to_stub_filtered, key=lambda x: x.name))])

    # Write into target
    with open(stub_file, 'a') as f:
        f.write("\n")
        f.write(stub_str)



##-- ifmain
if __name__ == '__main__':
    main()

##-- end ifmain
