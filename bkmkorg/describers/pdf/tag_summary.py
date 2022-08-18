#!/usr/bin/env python

##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
from datetime import datetime
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import pathlib as pl
import bibtexparser as b
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bibtex import entry_processors as bib_proc
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
parser.add_argument('--tag')
parser.add_argument('--target', action='append', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--bound', default=200)
##-- end argparse

def main():
    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()

    output_path = args.output /  f"{args.tag}_summary"

    bibtex_files = retrieval.get_data_files(args.target, ".bib")
    db = b.bibdatabase.BibDatabase()
    BU.parse_bib_files(bibtex_files, func=bib_proc.tag_summary, database=db)

    entries_with_tag = [x for x in db.entries if args.tag in x['tags']]
    entries_by_year  = sorted(entries_with_tag, key=lambda x: x['year'])
    pdfs_to_process  = [x['file'] for x in entries_by_year]
    expanded_paths   = [pl.Path(x).expanduser().resolve() for x in pdfs_to_process]
    logging.info("Summarising %s pdfs", len(expanded_paths))
    PU.summarise_pdfs(expanded_paths, output=output_path, bound=args.bound)


if __name__ == "__main__":
    main()
