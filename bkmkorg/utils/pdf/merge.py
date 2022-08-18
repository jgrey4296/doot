#!/usr/bin/env python
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.pdf import pdf as PU
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
parser.add_argument('--target', action="append", required=True)
parser.add_argument('--output', required=True)
##-- end argparse


if __name__ == "__main__":
    args        = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()

    # Find all pdfs in subdir
    pdfs_to_process = retrieval.get_data_files(args.target, ".pdf")
    logging.info("Merging %s pdfs", len(pdfs_to_process))
    PU.merge_pdfs(pdfs_to_process, output=args.output)

    # writer.trailer.Info = IndirectPdfDict(
    #     Title='your title goes here',
    #     Author='your name goes here',
    #     Subject='what is it all about?',
    #     Creator='some script goes here',
    # )
