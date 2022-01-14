#!/usr/bin/env python
# https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
import argparse
import logging as root_logger
from datetime import datetime
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import bibtexparser as b
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.pdf import pdf as PU

# Setup root_logger:
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join([""]))
parser.add_argument('--tag')
parser.add_argument('--target', action='append')
parser.add_argument('--output')
parser.add_argument('--bound', default=200)



def main():
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))

    output_path = join(args.output, "{}_summary".format(args.tag))

    bibtex_files = retrieval.get_data_files(args.target, ".bib")
    db = b.bibdatabase.BibDatabase()
    BU.parse_bib_files(bibtex_files, func=bib_proc.tag_summary, database=db)

    entries_with_tag = [x for x in db.entries if args.tag in x['tags']]
    entries_by_year  = sorted(entries_with_tag, key=lambda x: x['year'])
    pdfs_to_process  = [x['file'] for x in entries_by_year]
    expanded_paths   = [abspath(expanduser(x)) for x in pdfs_to_process]
    logging.info("Summarising {} pdfs".format(len(expanded_paths)))
    PU.summarise_pdfs(expanded_paths, output=output_path, bound=args.bound)


if __name__ == "__main__":
    main()
