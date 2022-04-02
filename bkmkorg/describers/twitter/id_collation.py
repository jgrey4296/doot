"""
Extract Twitter ID's from org files

"""
import argparse
import logging as root_logger
from math import ceil
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
# https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import bibtexparser as b
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.org.extraction import get_tweet_dates_and_ids

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="\n".join(["Extracts all tweet ids in all org files in specified dirs"]))
parser.add_argument('-t', '--target', action="append", required=True)
parser.add_argument('-o', '--output', default="collected")
#--------------------------------------------------


if __name__ == "__main__":
    logging.info("Twitter ID Extractor start: --------------------")
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))

    logging.info("Targeting: {}".format(args.target))
    logging.info("Output to: {}".format(args.output))

    bibs, htmls, orgs, bkmks = retrieval.collect_files(args.target)
    tweets : List[Tuple[str, str]] = get_tweet_dates_and_ids(orgs)
    ids_set = {x[0] for x in tweets}

    logging.info("Found {} unique twitter ids".format(len(ids_set)))
    with open(args.output,'w') as f:
        for id_str in ids_set:
            f.write("{}\n".format(id_str))

    logging.info("Complete --------------------")
