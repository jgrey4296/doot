"""
Extract Twitter ID's from org files

"""

##-- imports
from __future__ import annotations

import pathlib as pl
import argparse
import logging as root_logger
from math import ceil
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import bibtexparser as b
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.org.extraction import get_tweet_dates_and_ids
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
                                    epilog="\n".join(["Extracts all tweet ids in all org files in specified dirs"]))
parser.add_argument('-t', '--target', action="append", required=True)
parser.add_argument('-o', '--output', default="collected")
##-- end argparse



if __name__ == "__main__":
    logging.info("Twitter ID Extractor start: --------------------")
    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    args.target = [pl.Path(x).expanduser().resolve() for x in args.target]

    logging.info("Targeting: %s", args.target)
    logging.info("Output to: %s", args.output)

    bibs, htmls, orgs, bkmks = retrieval.collect_files(args.target)
    tweets : List[Tuple[str, str]] = get_tweet_dates_and_ids(orgs)
    ids_set = {x[0] for x in tweets}

    logging.info("Found %s unique twitter ids", len(ids_set))
    with open(args.output,'w') as f:
        for id_str in ids_set:
            f.write("{}\n".format(id_str))

    logging.info("Complete --------------------")
