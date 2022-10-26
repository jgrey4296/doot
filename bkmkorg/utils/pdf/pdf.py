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

    if output.exists():
        logging.info("Overwriting existing summary")

    for path in paths:
        try:
            logging.info("File : %s", path.name)
            pdf_obj = PdfReader(path)
            for x in pdf_obj.pages:
                writer.addpage(x)
        except:
            logging.warning("Error Encountered with %s", path)

    writer.write(str(output))



##-- pdf summary
def summarise_to_pdfs(paths:list[pl.Path], func=None, output="./pdf_summary", base_name="summary", bound=200):
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
            # Try to add to the writer in various forms:
            for attempt in [handle_epub, add_to_writer, uncompress_pdf, add_simple_text_to_writer]:
                if attempt(path, writer, func, temp_dir):
                    break
                else:
                    continue

            count, writer = finalise_writer(output, writer, base_name, count, bound)

        finalise_writer(output, writer, base_name, count, bound, force=True)


def handle_epub(path, writer, func, temp) -> bool:
    result = False
    if path.suffix == ".epub":
        logging.info("Handling epub: %s", path)
        temp_file_name = pl.Path(temp) / f"{uuid4().hex}.pdf"
        try:
            pandoc.convert_file([str(path)], "pdf", outputfile=str(temp_file_name), format="epub")
            pdf_obj = PdfReader(temp_file_name)
            writer.addpage(func(pdf_obj))
            result = True
        except Exception as err:
            logging.info("Epub Handling Failed: %s", path)
            logging.debug("Epub Error: %s", err)

    return result

def add_to_writer(path, writer, func, temp) -> bool:
    logging.warning("Adding to writer: %s", path)
    result = False
    try:
        if path.suffix == ".pdf":
            pdf_obj = PdfReader(path)
            writer.addpage(func(pdf_obj))
            result = True
    finally:
        return result

def uncompress_pdf(path, writer, func, temp):
    if path.suffix != ".pdf":
        return False

    logging.warning("Attempting to uncompress then add: %s", path)
    temp_unc   = pl.Path(temp) / f"{path.stem}_uncompressed.pdf"
    temp_comp  = pl.Path(temp) / f"{path.stem}_compressed.pdf"
    result = run(['pdftk', str(path), "output", str(temp_unc), "uncompress"],
                 capture_output=True)
    # result = run(['pdftk', str(temp_unc), "output", str(temp_comp), "uncompress"],
    #              capture_output=True)
    return add_to_writer(temp_unc,writer, func, temp)


def add_simple_text_to_writer(path, writer, func, temp):
    logging.warning("Adding Simple Text to Writer: %s", path)
    # from stackoverflow.com/questions/2365411
    # if not path.isascii():
    #     path = unicodedata.normalize("NFKD", path).encode("ascii", "ignore")

    temp_file_name = pl.Path(temp) / f"{uuid4().hex}.pdf"
    simple_path = "/".join(path.parts[-4:])
    pandoc.convert_text(f"File: {simple_path}", "pdf", outputfile=str(temp_file_name), format="md")
    pdf_obj = PdfReader(temp_file_name)
    writer.addpage(func(pdf_obj))
    return True

def finalise_writer(output, writer, base_name, count, bound, force=False) -> tuple[int, PdfWriter]:


    if force or len(writer.pagearray) > bound:
        logging.warning("Writing and incrementing")
        writer.trailer.Info = IndirectPdfDict(
            Title=f'Pdf Summary of {base_name} : Number: {count}',
            Author='JG',
            Subject='pdf summary',
            Creator='bkmkorg.utils.pdf.pdf.summarise_to_pdfs',
        )
        if output.with_stem(f"{output.stem}_{count}").exists():
            logging.info("Overwriting existing summary")
        writer.write(output.with_stem(f"{output.stem}_{count}"))
        writer = PdfWriter()
        count += 1

    return count, writer

##-- end pdf summary
