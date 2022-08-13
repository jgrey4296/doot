#/usr/bin/env python3
"""
Process all bibtex entries,
adding metadata to the pdf files
"""
##-- imports
from __future__ import annotations

import abc
import argparse
import logging as logmod
import pathlib as pl
import re
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import bibtexparser as b
from bibtexparser.customization import splitname
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bibtex.writer import JGBibTexWriter
from bkmkorg.utils.dfs.files import get_data_files
from pdfrw import PdfName, PdfReader, PdfWriter

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- Logging
DISPLAY_LEVEL = logmod.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
LOG_FORMAT    = "%(asctime)s | %(levelname)8s | %(message)s"
FILE_MODE     = "w"
STREAM_TARGET = stdout

logger          = logmod.getLogger(__name__)
console_handler = logmod.StreamHandler(STREAM_TARGET)
file_handler    = logmod.FileHandler(LOG_FILE_NAME, mode=FILE_MODE)

console_handler.setLevel(DISPLAY_LEVEL)
# console_handler.setFormatter(logmod.Formatter(LOG_FORMAT))
file_handler.setLevel(logmod.DEBUG)
# file_handler.setFormatter(logmod.Formatter(LOG_FORMAT))

logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.setLevel(logmod.DEBUG)
logging = logger
##-- end Logging

##-- argparse
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Update metadata of pdf files mentioned",
                                                     "in library's bibtex files"]))
parser.add_argument('--library', required=True)
##-- end argparse

##-- regexs
FILE_RE   = re.compile(r"^file(\d*)")
##-- end regexs

def add_metadata(path:pl.Path, bib_entry:dict, bib_str:str):
    logging.info("Adding Metadata to %s", path)
    pdf = PdfReader(path)
    assert(PdfName('Info') in pdf.keys())
    for key in (set(bib_entry.keys()) - {'ID', 'ENTRYTYPE'}):
        name = PdfName(key.capitalize())
        match name in pdf.Info:
            case False:
                pdf.Info[name] = bib_entry[key]
            case True if pdf.Info[name] == f"({bib_entry[key]})":
                pass
            case True if pdf.Info[name] == "()":
                pdf.Info[name] = bib_entry[key]
            case True if pdf.Info[name] == "":
                pdf.Info[name] = bib_entry[key]
            case True if (pdf.Info[name] != bib_entry[key]
                          and input(f"Overwrite: {key}: {pdf.Info[name]} -> {bib_entry[key]}? */n ") != "n"):
                pdf.Info[name] = bib_entry[key]

    pdf.Info.Bibtex = bib_str

    author_head = "_".join(splitname(bib_entry['author'].split(' and ')[0])['last'])
    title = bib_entry['title'].replace(' ', '_')[:min(30, bib_entry['title'].index(':') if ':' in bib_entry['title'] else len(bib_entry['title']))]
    new_name = f"md_{bib_entry['year']}_{author_head}_{title}"
    new_path = path.parent / f'{new_name}{path.suffix}'
    logging.info(f"Writing To: {new_path.name}")
    PdfWriter(new_path, trailer=pdf).write()

##-- main
def main():
    args     = parser.parse_args()
    library  = pl.Path(args.library)

    writer   = JGBibTexWriter()
    all_bibs = get_data_files(library, ".bib")
    main_db  = BU.parse_bib_files(all_bibs)


    logging.info("Loaded Database: {} entries".format(len(main_db.entries)))

    count = 0
    for i, entry in enumerate(main_db.entries):
        if i % 10 == 0:
            logging.info("{}/10 Complete".format(count))
            count += 1
        unicode_entry = b.customization.convert_to_unicode(entry)

        file_keys = [x for x in unicode_entry.keys() if FILE_RE.search(x)]
        for fk in file_keys:
            path = pl.Path(unicode_entry[fk])
            if path.suffix == ".pdf" and path.exists():
                entry_as_str : str = writer._entry_to_bibtex(entry)
                add_metadata(path, unicode_entry, entry_as_str)


if __name__ == '__main__':
    main()
##-- end main
