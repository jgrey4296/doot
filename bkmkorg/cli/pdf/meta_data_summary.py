#!/usr/bin/env python
"""
Finds all pdf's and epubs,
and uses exiftool and pdftk to extract metadata from them

"""
##-- imports
from __future__ import annotations
import argparse
import subprocess
import logging as logmod
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import pathlib as pl
from bkmkorg.bibtex import parsing as BU
from bkmkorg.pdf import manipulate as PU
from bkmkorg.files import collect
##-- end imports

##-- logging
LOGLEVEL = logmod.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
logmod.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = logmod.StreamHandler()
console.setLevel(logmod.INFO)
logmod.getLogger('').addHandler(console)
logging = logmod.getLogger(__name__)
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Create summary pdf of the first 2 pages of all pdfs in target",
                                                        "If `grouped` then create multiple summaries, one for each immediate subdirectory of `target`"]))
parser.add_argument('--target', required=True)
parser.add_argument('--output', help="Output Path and base file name. ie: a/path/blah -> blah_{}.pdf", required=True)
parser.add_argument('--bound', default=200)

##-- end argparse
END_LINE = "---%%%--- Finished"

def file_is_finished(path) -> bool:
    result = False
    if not path.exists():
        return result

    response = subprocess.run(['tail', '-n', '1', str(path)],
                              capture_output=True)
    line = response.stdout.decode()
    if line == END_LINE:
        result = True

    return result


def exiftool_pdf_md(path) -> str:
    result = ""
    try:
        response = subprocess.run(["exiftool", str(path), "-PDF:all"],
                                  capture_output=True)
        result = response.stdout.decode() if response.returncode == 0 else response.stderr.decode()

    except Exception as err:
        result = str(err)

    return result


def exiftool_xmp_md(path) -> str:
    result = ""
    try:
        response = subprocess.run(["exiftool", str(path), "-XMP:all"],
                                  capture_output=True)
        result = response.stdout.decode() if response.returncode == 0 else response.stderr.decode()

    except Exception as err:
        result = str(err)

    return result

def pdftk_md(path) -> str:
    result = ""
    try:
        response = subprocess.run(["pdftk", str(path), "dump_data_utf8"],
                                  capture_output=True)
        result = response.stdout.decode() if response.returncode == 0 else response.stderr.decode()

        result = "\n".join([x for x in result.split("\n") if "Info" in x])


    except Exception as err:
        result = str(err)

    return result

def main():
    args        = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    args.target = pl.Path(args.target)
    assert(args.output.suffix != "")

    pdfs_to_process = collect.get_data_files(args.target, [".pdf", ".epub"])

    if not args.output.parent.exists():
        args.output.parent.mkdir()

    proportion = int(max(1, len(pdfs_to_process) / 10))
    last_out   = None
    for i, path in enumerate(pdfs_to_process):
        if i % proportion == 0:
            logging.info("%s/10 Complete", i * proportion)

        out_path = args.output.with_stem(f"{args.output.stem}_{path.parent.parent.name}")
        if not last_out and file_is_finished(out_path):
            logging.info("Skipping: %s", path.parent.parent.name)
            continue
        elif last_out and out_path != last_out:
            with open(last_out, 'a') as f:
                f.write("\n\n" + END_LINE)
            logging.info("Starting: %s", path.parent.parent.name)

        # Get the metadata
        etm    = exiftool_pdf_md(path) if path.suffix == ".pdf" else ""
        etxmpm = exiftool_xmp_md(path)
        pdftkm = pdftk_md(path) if path.suffix == ".pdf" else ""

        short_path = path.relative_to(path.parent.parent.parent)

        out_path = args.output.with_stem(f"{args.output.stem}_{path.parent.parent.name}")
        with open(out_path, 'a') as f:
            f.write("----- File: " + str(short_path) + "\n")
            f.write("----- Pdf MetaData (Exiftool):\n")
            f.write(etm + "\n")
            f.write("----- Pdf XMP MetaData (Exiftool):\n")
            f.write(etxmpm + "\n")
            f.write("----- Pdf MetaData (PdfTK):\n")
            f.write(pdftkm + "\n")
            f.write("--------------------------------------------------\n")

        last_out = out_path

##-- ifmain
if __name__ == "__main__":
    main()

##-- end ifmain
