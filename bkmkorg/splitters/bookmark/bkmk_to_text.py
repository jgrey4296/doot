#!/usr/bin/env python
##-- imports
from __future__ import annotations

import pathlib as pl
import argparse
import logging as root_logger
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.utils.bookmarks.collection import BookmarkCollection
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
                                    epilog = "\n".join(["Split bookmarks into a text file"]))
parser.add_argument('-s', '--source', help="Expects a netscape html bookmark file", required=True)
parser.add_argument('-o', '--output', help="Expects a .bookmarks filename", required=True)
##-- end argparse

def main():
    args = parser.parse_args()
    args.source = pl.Path(args.source).expanduser().resolve()
    args.output = pl.Path(args.output).expanduser().resolve()

    assert(args.source.exists())
    assert(not args.output.exists())

    logging.info("Loading source")
    source = BookmarkCollection.read_netscape(args.source)

    # Print as plain text
    as_text = str(source)
    with open(args.output, 'w') as f:
        f.write(as_text)


if __name__ == '__main__':
    main()
