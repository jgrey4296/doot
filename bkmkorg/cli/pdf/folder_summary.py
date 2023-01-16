#!/usr/bin/env python
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
from random import choice
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import pathlib as pl
from bkmkorg.bibtex import parsing as BU
from bkmkorg.pdf import manipulate as PU
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
                                    epilog = "\n".join(["Create summary pdf of the first 2 pages of all pdfs in target",
                                                        "If `grouped` then create multiple summaries, one for each immediate subdirectory of `target`"]))
parser.add_argument('--target', required=True)
parser.add_argument('--output', help="Output Path and base file name. ie: a/path/blah -> blah_{}.pdf", required=True)
parser.add_argument('-g', '--grouped', action='store_true')
parser.add_argument('--bound', default=200)
parser.add_argument('-r', '--random', action='store_true')
##-- end argparse


# TODO, get information from bibtex on each entry, including specific pages
def main():
    args        = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    args.target = pl.Path(args.target).expanduser().resolve()

    logging.info("Summarising Target: %s", args.target)
    logging.info("Summarising to output: %s", args.output)

    if args.random:
        assert(args.target.is_dir()), args.target
        available = list(args.target.iterdir())
        chosen    = choice(available)
        pdfs_to_process = collect.get_data_files(chosen, [".pdf", ".epub"])
        logging.info("Summarising %s's %s pdfs", chosen, len(pdfs_to_process))
        PU.summarise_to_pdfs(pdfs_to_process,
                             output=args.output,
                             base_name=chosen.stem,
                             bound=int(args.bound))


    elif args.grouped:
        assert(args.target.is_dir())
        for group in args.target.iterdir():
            if bool(list(args.output.glob(f"{group.stem}*.pdf"))):
                continue
            pdfs_to_process = collect.get_data_files(group, [".pdf", ".epub"])
            logging.info("Summarising %s's %s pdfs", group, len(pdfs_to_process))
            PU.summarise_to_pdfs(pdfs_to_process,
                              output=args.output,
                              base_name=group.stem,
                              bound=int(args.bound))
    else:
        # Find all pdfs in subdir
        pdfs_to_process = collect.get_data_files(args.target, ".pdf")
        logging.info("Summarising %s pdfs", len(pdfs_to_process))
        PU.summarise_to_pdfs(pdfs_to_process,
                          output=args.output,
                          base_name=args.target.stem,
                          bound=args.bound)



##-- ifmain
if __name__ == "__main__":
    main()

##-- end ifmain
