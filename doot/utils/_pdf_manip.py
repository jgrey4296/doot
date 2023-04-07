#!/usr/bin/env python
##-- imports
from __future__ import annotations

import logging as root_logger
import pathlib as pl
import subprocess
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from uuid import uuid4


##-- end imports

logging = root_logger.getLogger(__name__)


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
            Creator='doot.pdf.manipluate.summarise_to_pdfs',
        )
        if output.with_stem(f"{output.stem}_{count}").exists():
            logging.info("Overwriting existing summary")
        writer.write(output.with_stem(f"{output.stem}_{count}"))
        writer = PdfWriter()
        count += 1

    return count, writer


def file_is_finished(path) -> bool:
    result = False
    if not path.exists():
        return result

    response = subprocess.run(['tail', '-n', '1', str(path)],
                              capture_output=True,
                              shell=False)
    line = response.stdout.decode()
    if line == END_LINE:
        result = True

    return result

def exiftool_pdf_md(path) -> str:
    result = ""
    try:
        response = subprocess.run(["exiftool", str(path), "-PDF:all"],
                                  capture_output=True,
                                  shell=False)
        result = response.stdout.decode() if response.returncode == 0 else response.stderr.decode()

    except Exception as err:
        result = str(err)

    return result

def exiftool_xmp_md(path) -> str:
    result = ""
    try:
        response = subprocess.run(["exiftool", str(path), "-XMP:all"],
                                  capture_output=True,
                                  shell=False)
        result = response.stdout.decode() if response.returncode == 0 else response.stderr.decode()

    except Exception as err:
        result = str(err)

    return result

def pdftk_md(path) -> str:
    result = ""
    try:
        response = subprocess.run(["pdftk", str(path), "dump_data_utf8"],
                                  capture_output=True,
                                  shell=False)
        result = response.stdout.decode() if response.returncode == 0 else response.stderr.decode()

        result = "\n".join([x for x in result.split("\n") if "Info" in x])

    except Exception as err:
        result = str(err)

    return result
