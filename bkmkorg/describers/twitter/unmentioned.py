#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
import pathlib as pl
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.utils.dfs.files import get_data_files
from bkmkorg.utils.indices.collection import IndexFile
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
parser.add_argument('--aBool', action="store_true")
parser.add_argument('--target', append=True, required=True)
parser.add_argument('--tags', required=True)
parser.add_argument('--out', required=True)
##-- end argparse

def main():
    args      = parser.parse_args()
    args.out  = pl.Path(args.out).expanduser().resolve()
    args.tags = pl.Path(args.tags).expanduser().resolve()

    found     = set(get_data_files(args.target, ".org"))
    tag_index = IndexFile.builder(args.tags)

    for tag, mentioned in tag_index.items():
        found.difference_update(mentioned)

    # Write report
    with open(args.out) as f:
        f.write("\n".join(sorted(found)))

if __name__ == '__main__':
    main()
