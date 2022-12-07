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
import fitz
import re
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
import subprocess
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import bibtexparser as b
from bibtexparser.customization import splitname
from bkmkorg.bibtex import parsing as BU
from bkmkorg.bibtex.writer import JGBibTexWriter
from bkmkorg.files.collect import get_data_files
from pdfrw import PdfName, PdfReader, PdfWriter

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- regexs
FILE_RE   = re.compile(r"^file(\d*)")
##-- end regexs

logging = logmod.getLogger(__name__)

def check_pdf(path:pl.Path):
    results = subprocess.run(["pdfinfo", str(path)],
                             capture_output=True)
    assert(results.returncode == 0), path

def add_metadata(path:pl.Path, bib_entry:dict, bib_str:str):
    # using fitz / pymupdf
    logging.info("Adding Metadata to %s", path)
    pdf = fitz.Document(path)
    metadata = pdf.metadata
    if 'author' in bib_entry and bib_entry['author'] != "":
        metadata['author'] = bib_entry['author']
    elif 'editor' in bib_entry and bib_entry['editor'] != "":
        metadata['author'] = bib_entry['editor']

    pdf.set_metadata(metadata)

    lines = bib_str.strip().split("\n")
    xml_data = "<bibtex>" + " ".join([f"<line>{x}</line>" for x in lines]) + "</bibtex>"
    pdf.set_xml_metadata(xml_data)

    new_path    = path.with_stem("md_" + path.stem)
    logging.info("Writing To: %s", new_path.name)
    pdf.save(str(new_path))
    pdf.close()

def add_metadata_alt(path:pl.Path, bib_entry:dict, bib_str:str):
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
    title       = bib_entry['title'].replace(' ', '_')[:min(30, bib_entry['title'].index(':') if ':' in bib_entry['title'] else len(bib_entry['title']))]
    new_name    = f"md_{bib_entry['year']}_{author_head}_{title}"
    new_path    = path.parent / f'{new_name}{path.suffix}'
    logging.info("Writing To: %s", new_path.name)
    PdfWriter(new_path, trailer=pdf).write()
