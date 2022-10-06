#!/usr/bin/env python
"""
Check Bibtex library against pdf library
Output bibtex entries without matching files,
and files without matching entries
"""
##-- imports
import argparse
import logging as root_logger
import re
from unicodedata import normalize

import pathlib as pl
import bibtexparser as b
from bibtexparser import customization as c

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
##-- end imports

##-- regexs
PATH_NORM = re.compile("^.+?pdflibrary")
FILE_RE   = re.compile(r"^file(\d*)")
##-- end regexs

##-- logging
LOGLEVEL      = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="\n".join(["Check All pdfs are accounted for in a bibliography"])
                                    )
parser.add_argument('-t', '--target',  help="Pdf Library directory to verify", required=True)
parser.add_argument('-l', '--library', help="Bibtex Library directory to verify", required=True)
parser.add_argument('-o', '--output',  help="Output location for reports", required=True)
##-- end argparse

LIB_ROOT = pl.Path("~/pdflibrary").expanduser().resolve()

def get_mentions(entries) -> set[pl.Path]:
    mentions = set()
    # Convert entries to unicode
    for i, entry in enumerate(entries):
        entry_keys = [x for x in entry.keys() if FILE_RE.search(x)]
        for k in entry_keys:
            if entry[k][0] not in  "~/":
                fp = LIB_ROOT / entry[k]
            else:
                fp = pl.Path(entry[k])

            mentions.add(fp.expanduser().resolve())

    return mentions

def main():
    args = parser.parse_args()

    args.output  = pl.Path(args.output).expanduser().resolve()
    args.library = pl.Path(args.library).expanduser().resolve()
    args.target  = pl.Path(args.target).expanduser().resolve()

    assert(args.library.exists())
    assert(args.output.exists())
    assert(args.target.exists())

    # Get targets
    all_bibs = retrieval.get_data_files(args.library, ".bib")
    main_db = BU.parse_bib_files(all_bibs)

    logging.info("Loaded Database: %s entries", len(main_db.entries))
    existing : set[pl.Path] = {x for x in retrieval.get_data_files(args.target, [".epub", ".pdf"])}
    mentions : set[pl.Path] = get_mentions(main_db.entries)

    logging.info("Found %s files mentioned in bibliography", len(mentions))
    logging.info("Found %s files existing", len(existing))

    mentioned_non_existent = mentions - existing
    existing_not_mentioned = existing - mentions

    logging.info("Mentioned but not existing: %s", len(mentioned_non_existent))
    logging.info("Existing but not mentioned: %s", len(existing_not_mentioned))

    relative_non_existent  : set[str] = set(str(x.relative_to(LIB_ROOT)) for x in mentioned_non_existent if x.is_relative_to(LIB_ROOT))
    relative_not_mentioned : set[str] = set(str(x.relative_to(LIB_ROOT)) for x in existing_not_mentioned if x.is_relative_to(LIB_ROOT))
    # Create output files
    with open(args.output / "bibtex.not_existing",'w') as f:
        f.write("\n".join(sorted(relative_non_existent)))

    with open(args.output / "bibtex.not_mentioned", 'w') as f:
        f.write("\n".join(sorted(relative_not_mentioned)))


if __name__ == "__main__":
    main()
