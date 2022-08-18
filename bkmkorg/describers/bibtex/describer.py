#!/usr/bin/env python
"""
Script to process bibtex file
Giving stats, non-tagged entries,
year distributions
firstnames, surnames.
"""
##-- imports
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

import pathlib as pl
import argparse
import logging as root_logger
from math import ceil
from collections import defaultdict
from dataclasses import dataclass, field, InitVar

import bibtexparser as b
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.diagram import make_bar
from bkmkorg.utils.tag.collection import TagFile

##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

# Setup
console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparse
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="\n".join(["Describe a bibtex file's:",
                                                    "Tags, year counts, authors,",
                                                    "And entries lacking files or with multiple files"]))
parser.add_argument('-t', '--target', default="~/github/writing/resources", help="Input target")
parser.add_argument('-o', '--output', default="bibtex",                     help="Output Target")
##-- end argparse

@dataclass
class ProcessResults:

    all_keys      : List[str] = field(default_factory=list)
    all_years     : TagFile   = field(default_factory=TagFile)
    author_counts : TagFile   = field(default_factory=TagFile)
    non_tagged    : List[str] = field(default_factory=list)
    no_file       : List[str] = field(default_factory=list)
    missing_files : List[str] = field(default_factory=list)
    duplicates    : Set[str]  = field(default_factory=set)

def process_db(db):

    proportion = int(len(db.entries) / 10)
    count = 0

    # Extracted data
    results = ProcessResults()

    # Enumerate over all entries, updated data
    for i, entry in enumerate(db.entries):
        # Log progress
        if i % proportion == 0:
            logging.info(f"%s/10 Complete", count)
            count += 1

        if entry['ID'] in results.all_keys:
            logging.warning("Duplicate Key: %s", entry['ID'])
            results.duplicates.add(entry['ID'])

        results.all_keys.append(entry['ID'])
        # get tags
        e_tags = entry['tags']

        # get untagged
        if not bool(e_tags):
            results.non_tagged.append(entry)

        # count entries per year
        if 'year' in entry:
            results.all_years.inc(entry['year'])

        # count names
        for x in entry['p_authors']:
            for name in x:
                results.author_counts.inc(name, clean=False)


        # Retrieve file information
        if not any(['file' in x for x in entry.keys()]):
            results.no_file.append(entry['ID'])

        else:
            filenames              = [y for x,y in entry.items() if 'file' in x]
            results.missing_files += [y for y in filenames if not pl.Path(y).expanduser().resolve().exists()]

    return results

def main():
    args = parser.parse_args()

    args.output = pl.Path(args.output).expanduser().resolve()
    assert(args.target.exists())

    logging.info("Targeting: %s", args.target)
    logging.info("Output to: %s", args.output)

    # Load targets
    bib_files = retrieval.get_data_files(args.target, ".bib")
    db        = BU.parse_bib_files(bib_files, func=bib_proc.clean_full)
    logging.info("Bibtex loaded")

    logging.info(f"Processing Entries: %s", len(db.entries))
    result = process_db(db)
    logging.info("Processing complete")


    with open(args.output / "bibtex.years", 'w') as f:
        f.write(str(result.all_years))

    with open(args.output / "bibtex.authors", 'w') as f:
        f.write(str(result.author_counts))

    with open(args.output / "bibtex.no_file", 'w') as f:
        f.write("\n".result.no_file))

    with open(args.output / "bibtex.missing_file", 'w') as f:
        f.write("\n".result.missing_files))

    with open(args.output / "bibtex.duplicates", 'w') as f:
        f.write("\n".result.duplicates))

    with open(args.output / "bibtex.untagged", 'w') as f:
        f.write("\n".result.non_tagged))

    logging.info("Complete")


if __name__ == "__main__":
    main()
