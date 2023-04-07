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

END_LINE : Final = "---%%%--- Finished"

class PdfMixin:

    def pdf_get_info(self, fpath):
        assert(fpath.suffix == ".pdf")
        cmd = self.cmd("pdftk", fpath, "dump_data_utf8")
        cmd.execute()
        return cmd.out

    def pdf_update_info(self, fpath:pl.Path, info:pl.Path, output=None):
        assert(fpath.suffix == ".pdf")
        output = output or fpath.with_suffix(".updated.pdf")
        cmd    = self.cmd("pdftk", fpath, "update_info_utf8", info, "output", output)
        cmd.execute()
        return cmd.out

    def pdf_attach_to(self, fpath, files:list, output=None):
        assert(fpath.suffix == ".pdf")
        output = output or fpath.with_suffix(".attached.pdf")
        cmd = self.cmd("pdftk", fpath, "attach_files", *files, "output", output)
        cmd.execute()
        return output

    def pdf_extract_from(self, fpath, output=None):
        assert(fpath.suffix == ".pdf")
        output = output or fpath.parent / f"{fpath.name}_files"
        cmd = self.cmd("pdftk", fpath, "upack_files", "output", output)
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
        cmd = self.cmd("pdftk", fpath, "upack_files", "output", output)
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