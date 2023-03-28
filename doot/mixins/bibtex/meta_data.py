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
import subprocess
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

import fitz
from bibtexparser.customization import splitname
from doot.mixins.bibtex.writer import JGBibTexWriter
from pdfrw import PdfName, PdfReader, PdfWriter

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- regexs
FILE_RE : Final  = re.compile(r"^file(\d*)")
##-- end regexs

logging = logmod.getLogger(__name__)

class PdfMetaDataMixin:

    def check_pdf(self, path:pl.Path):
        raise NotImplementedError()
        results = subprocess.run(["pdfinfo", str(path)],
                                capture_output=True,
                                shell=False)
        assert(results.returncode == 0), path

    def add_metadata(self, path:pl.Path, bib_entry:dict, bib_str:str):
        raise NotImplementedError()
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

    def add_metadata_alt(self, path:pl.Path, bib_entry:dict, bib_str:str):
        raise NotImplementedError()
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



    def add_metadata_to_db(self, db):
        raise NotImplementedError()
        writer   = JGBibTexWriter()
        count = 0
        for i, entry in enumerate(db.entries):
            if i % 10 == 0:
                logging.info("%s/10 Complete", count)
                count += 1

            record = c.convert_to_unicode(entry)

            file_fields = [x for x in record.keys() if 'file' in x]
            for field in file_fields:
                fp          = make_path(record[field])
                orig_parent = fp.parent

                if fp.suffix == ".pdf" and fp.exists():
                    entry_as_str : str = writer._entry_to_bibtex(entry)
                    add_metadata(fp, record, entry_as_str)
