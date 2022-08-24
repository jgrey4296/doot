#!/usr/bin/env python
##-- imports
from __future__ import annotations

import logging as root_logger
import pathlib as pl
import subprocess
import tempfile
from subprocess import call, run
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from uuid import uuid4

import pypandoc as pandoc
from pdfrw import IndirectPdfDict, PageMerge, PdfReader, PdfWriter
##-- end imports

logging = root_logger.getLogger(__name__)


def get2(srcpages):
    scale = 0.5
    srcpages = PageMerge() + srcpages.pages[:2]
    x_increment, y_increment = (scale * i for i in srcpages.xobj_box[2:])
    for i, page in enumerate(srcpages):
        page.scale(scale)
        page.x = 0 if i == 0 else x_increment
        page.y = 0

    return srcpages.render()


def summarise_pdfs(paths:list[pl.Path], func=None, output="./pdf_summary", base_name="summary", bound=200):
    """
    For a list of pdfs, get the first two pages of each,
    and make a pdf of those
    """
    output = pl.Path(output).expanduser().resolve()
    count = 0
    func = func or get2
    if output.is_dir() and not output.exists():
        output.mkdir()
    if output.is_dir():
        output = output / base_name

    output = output.with_suffix(".pdf")

    writer = PdfWriter()

    with tempfile.TemporaryDirectory() as temp_dir:
        for path in paths:
            try:
                if path.suffix == ".pdf":
                    pdf_obj = PdfReader(path)
                    writer.addpage(func(pdf_obj))
                else:
                    continue
            except:
                logging.warning("Error Encountered with %s", path)
                # from stackoverflow.com/questions/2365411
                # if not path.isascii():
                #     path = unicodedata.normalize("NFKD", path).encode("ascii", "ignore")

                temp_file_name = pl.Path(temp_dir) / f"{uuid4().hex}.pdf"
                pandoc.convert_text(f"File: {path}", "pdf", outputfile=str(temp_file_name), format="md")
                pdf_obj = PdfReader(temp_file_name)
                writer.addpage(func(pdf_obj))


            if len(writer.pagearray) > bound:
                # if pdf is too big, create another
                writer.trailer.Info = IndirectPdfDict(
                    Title=f'Pdf Summary of {base_name} : Number: {count}',
                    Author='JG',
                    Subject='pdf summary',
                    Creator='bkmkorg.utils.pdf.pdf.summarise_pdfs',
                )
                writer.write(output.with_stem(f"{output.stem}_{count}"))
                writer = PdfWriter()
                count += 1

    writer.trailer.Info = IndirectPdfDict(
        Title=f'Pdf Summary of {base_name} : Number : {count}',
        Author='JG',
        Subject='pdf summary',
        Creator='bkmkorg.utils.pdf.pdf.summarise_pdfs',
    )
    writer.write(output.with_stem(f"{output.stem}_{count}"))

def convert_pdfs_to_text(files:list[pl.Path]):
    logging.info("Converting %s files", len(files))
    for x in files:
        name = x.name
        text_file = x.parent / f".{name}.txt"
        if text_file.exists():
            continue

        call_sig = ['pdftotext', str(x), str(text_file)]
        logging.info("Converting: %s", " ".join(call_sig))
        call(call_sig)

def convert_alternative(source, output_dir, title):
    target = output_dir / f".{title}.txt"
    logging.info("Converting %s from %s", target, source)
    run(['mutool', 'convert', '-F', 'text', '-o', str(target), str(source)], stdout=subprocess.PIPE)


def merge_pdfs(paths, output="./pdf_summary"):
    output = pl.Path(output).expanduser().resolve().with_suffix(".pdf")
    writer = PdfWriter()

    for path in paths:
        try:
            logging.info("File : %s", path.name)
            pdf_obj = PdfReader(path)
            for x in pdf_obj.pages:
                writer.addpage(x)
        except:
            logging.warning("Error Encountered with %s", path)

    writer.write(str(output))
