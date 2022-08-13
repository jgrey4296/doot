#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
import random
from collections import defaultdict
import sys
from subprocess import run
from time import sleep
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import pathlib as pl
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.tag.collection import TagFile
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
                                 epilog = "\n".join(["Tag Grep",
                                                     "Use existing tags to index potential org files"]))
parser.add_argument('-l', '--library', action="append", required=True)
parser.add_argument('-t', '--target', action="append", required=True)
parser.add_argument('-o', '--output', required=True)
parser.add_argument('--file_batch', default=100, type=int)
parser.add_argument('--tag_batch',  default=100, type=int)
##-- end argparse

def main():
    logging.info("Grepping for Tags")
    args           = parser.parse_args()
    args.output    = pl.Path(args.output).expanduser().resolve()
    args.library   = [pl.Path(x).expanduser().resolve() for x in args.library]
    args.target    = [pl.Path(x).expanduser().resolve() for x in args.target]

    lock_file = args.output / ".lock"
    # Collect files to process
    lib            = retrieval.get_data_files(args.library, ext=".org")
    # Get tag set
    tags           = TagFile.builder(args.target)

    batch_count    = int(len(lib) / args.file_batch)
    processed_tags = TagFile.builder(args.output, ext=".index").to_set()

    # fail out if a lock file exists
    if lock_file.exists():
        logging.warning("Lock File Exists")
        sys.exit()

    lock_file.touch()
    assert(lock_file.exists())

    remaining_keys = list(set(tags.count.keys()).difference(processed_tags))

    logging.info("Total/Processed/Remaining: %s/%s/%s", len(tags), len(processed_tags), len(remaining_keys))
    logging.debug("Processed: %s", processed_tags)

    for i, tag in enumerate(remaining_keys[:args.tag_batch]):
        index_additions = IndexFile()
        ## batch filter files that mention the tag
        logging.info("-- Tag: %s %s/%s", tag, i, len(tags))
        batch_num = 0
        for start in range(0, len(lib), args.file_batch):
            logging.info(f"File Batch: %s/%s", batch_num, batch_count)
            result = run(['grep' , '-l', tag, *lib[start:start+args.file_batch]], capture_output=True)
            if result.returncode == 0 and bool(result.stdout):
                to_add : List = [x.strip() for x in result.stdout.decode().split("\n")]
                shortened     = [x[len(args.target[0]):] if args.target[0] in x else x for x in to_add]
                index_additions.add_files(tag, shortened)

            batch_num += 1

        # add new tag->file mappings to the index
        if bool(index_additions):
            logging.info("Writing to file: %s", len(index_additions))
            with open(args.output,'a') as f:
                f.write("\n")
                f.write(str(index_additions))

    lock_file.unlink()
    logging.info("Finished")

########################################
if __name__ == "__main__":
    main()
