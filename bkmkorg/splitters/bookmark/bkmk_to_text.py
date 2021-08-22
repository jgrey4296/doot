#!/usr/bin/env python
import argparse
import logging as root_logger
from os import listdir
# Setup root_logger:
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.io.reader.netscape import open_and_extract_bookmarks
from bkmkorg.io.writer.netscape import exportBookmarks

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Split bookmarks into a text file"]))
parser.add_argument('-s', '--source')
parser.add_argument('-o', '--output')

def main():
    args = parser.parse_args()
    args.source = abspath(expanduser(args.source))
    args.output = abspath(expanduser(args.output))

    assert(exists(args.source))

    logging.info("Loading source")
    source = open_and_extract_bookmarks(args.source)

    # Print as plain text
    output_lines = []
    for bkmk in source:
        tag_list = ":".join(bkmk.tags)
        output_lines.append(f"{bkmk.url} : {tag_list}")

    with open(args.output, 'w') as f:
        f.write("\n".join(output_lines))


if __name__ == '__main__':
    main()
