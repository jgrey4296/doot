#!/usr/bin/env python3
import argparse
import logging as root_logger
from os import listdir
# Setup root_logger:
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
from bkmkorg.utils.dfs.files import get_data_files
from bkmkorg.util.indices.collection import IndexFile


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join([""]))
    parser.add_argument('--aBool', action="store_true")
    parser.add_argument('--target', append=True)
    parser.add_argument('--tags')
    parser.add_argument('--out')

    args      = parser.parse_args()
    args.out  = abspath(expanduser(args.out))
    args.tags = abspath(expanduser(args.tags))

    found     = set(get_data_files(args.target, ".org"))
    tag_index = IndexFile.builder(args.tags)

    for tag, mentioned in tag_index.items():
        found.difference_update(mentioned)

    # Write report
    with open(args.out) as f:
        f.write("\n".join(sorted(found)))

if __name__ == '__main__':
    main()
