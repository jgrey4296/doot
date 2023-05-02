#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Final)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from pdfrw import IndirectPdfDict, PageMerge, PdfReader, PdfWriter
import pypandoc as pandoc
import subprocess
import tempfile
from bibtexparser.customization import splitname
from doot.mixins.bibtex.writer import JGBibTexWriter
from pdfrw import PdfName, PdfReader, PdfWriter

END_LINE : Final = "---%%%--- Finished"
FILE_RE : Final[re.Pattern]  = re.compile(r"^file(\d*)")

class PdfMixin:

    def pdf_get_info(self, fpath):
        assert(fpath.suffix == ".pdf")
        cmd = self.make_cmd("pdftk", fpath, "dump_data_utf8")
        cmd.execute()
        return cmd.out

    def pdf_update_info(self, fpath:pl.Path, info:pl.Path, output=None):
        assert(fpath.suffix == ".pdf")
        output = output or fpath.with_suffix(".updated.pdf")
        cmd    = self.make_cmd("pdftk", fpath, "update_info_utf8", info, "output", output)
        cmd.execute()
        return cmd.out

    def pdf_attach_to(self, fpath, files:list, output=None):
        assert(fpath.suffix == ".pdf")
        output = output or fpath.with_suffix(".attached.pdf")
        cmd = self.make_cmd("pdftk", fpath, "attach_files", *files, "output", output)
        cmd.execute()
        return output

    def pdf_extract_from(self, fpath, output=None):
        assert(fpath.suffix == ".pdf")
        output = output or fpath.parent / f"{fpath.name}_files"
        cmd = self.make_cmd("pdftk", fpath, "upack_files", "output", output)
        cmd.execute()
        return output
    def pdf_convert_to_text(self, files:list[pl.Path]):
        assert(all([f.suffix == ".pdf" for x in files]))
        logging.info("Converting %s files", len(files))
        for x in files:
            name = x.name
            text_file = x.parent / f".{name}.txt"
            if text_file.exists():
                continue

            call_sig = ['pdftotext', str(x), str(text_file)]
            logging.info("Converting: %s", " ".join(call_sig))
            call(call_sig)

    def pdf_merge(self, files:list, output=None):
        output = output or self.locs.build / "merged.pdf"
        cmd = self.make_cmd("pdftk", fpath, "upack_files", "output", output)
        cmd.execute()
        return output

    def pdf_summary(self, paths:list[pl.Path], bound=200, func=None, output=None):
        """
        For a list of pdfs, get the first two pages of each,
        and make a pdf of those
        """
        assert(all([x.suffix == ".pdf" for x in paths]))
        output = output or self.locs.build / "summary.pdf"
        func   = func or self._get_two_pages
        output = output.with_suffix(".pdf")
        writer = PdfWriter()
        count  = 0

        for path in paths:
            # Try to add to the writer in various forms:
            pdf_obj = PdfReader(path)
            writer.addpage(func(pdf_obj))

            if len(writer.pagearray) > bound:
                writer.trailer.Info = IndirectPdfDict(Title=f'Pdf Summary of {base_name} : Number: {count}', Author='JG', Subject='pdf summary', Creator=self.basename),
                writer.write(output.with_stem(f"{output.stem}_{count}"))
                writer = PdfWriter()
                count += 1

        if not len(writer.pagearray):
            return

        writer.trailer.Info = IndirectPdfDict(Title=f'Pdf Summary of {base_name} : Number: {count}', Author='JG', Subject='pdf summary', Creator=self.basename),
        writer.write(output.with_stem(f"{output.stem}_{count}"))

    def _get_two_pages(self, srcpages):
        scale = 0.5
        srcpages = PageMerge() + srcpages.pages[:2]
        x_increment, y_increment = (scale * i for i in srcpages.xobj_box[2:])
        for i, page in enumerate(srcpages):
            page.scale(scale)
            page.x = 0 if i == 0 else x_increment
            page.y = 0

        return srcpages.render()



class PdfMetaDataMixin:

    def check_pdf(self, path:pl.Path):
        raise NotImplementedError()
        results = subprocess.run(["pdfinfo", str(path)],
                                capture_output=True,
                                shell=False)
        assert(results.returncode == 0), path

    def add_metadata(self, path:pl.Path, bib_entry:dict, bib_str:str):
        raise NotImplementedError()
        # using pymupdf
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

            # record = c.convert_to_unicode(entry)

            file_fields = [x for x in record.keys() if 'file' in x]
            for field in file_fields:
                fp          = make_path(record[field])
                orig_parent = fp.parent

                if fp.suffix == ".pdf" and fp.exists():
                    entry_as_str : str = writer._entry_to_bibtex(entry)
                    add_metadata(fp, record, entry_as_str)
