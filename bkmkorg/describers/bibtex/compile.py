#/usr/bin/env python3
"""
Compile all bib files to pdf
"""
##-- imports
from __future__ import annotations

import abc
import argparse
import logging as logmod
from shutil import copy
import pathlib
import pathlib as pl
import subprocess
import tempfile
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from importlib.resources import files
from random import choice
from re import Pattern
from string import Template
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

from bkmkorg.utils.dfs import files as retrieval

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
logging = logmod.root
logging.setLevel(logmod.DEBUG)
##-- end logging

##-- data
data_path        = files("bkmkorg.__config")
compile_template = Template((data_path / "bib_compile_template.tex").read_text())
style_path       = str((data_path / "jg_custom.bst").with_suffix(""))
##-- end data

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Bibtex compilation"]))
parser.add_argument('--target', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--all', action="store_true")
##-- end argparse

def process_bib(bib_target, output):
    with tempfile.TemporaryDirectory() as temp_dir:
        logging.info("Temp Dir: %s", temp_dir)
        temp_dir_p = pl.Path(temp_dir)
        temp_tex = temp_dir_p / f"{bib_target.stem}.tex"
        temp_pdf = temp_dir_p / f"{bib_target.stem}.pdf"

        # write .tex
        with open(temp_tex, 'w') as f:
            f.write(compile_template.substitute(title=bib_target.stem,
                                                bibstyle=style_path,
                                                target=str(bib_target)))

        logging.info("First Pass")
        result = subprocess.run(["pdflatex", str(temp_tex.stem)],
                                capture_output=True,
                                cwd=str(temp_dir_p))
        logging.info("Bibtex Pass")
        handle_process_result(result)
        result = subprocess.run(["bibtex", str(temp_tex.stem)],
                                capture_output=True,
                                cwd=str(temp_dir_p))
        logging.info("Second Pass")
        handle_process_result(result)
        result = subprocess.run(["pdflatex", str(temp_tex.stem)],
                                capture_output=True,
                                cwd=str(temp_dir_p))
        logging.info("Third Pass")
        handle_process_result(result)
        result = subprocess.run(["pdflatex", str(temp_tex.stem)],
                                capture_output=True,
                                cwd=str(temp_dir_p))
        handle_process_result(result)

        # move to output
        assert(temp_pdf.exists())
        if (output / temp_pdf.name).exists():
            logging.info("Replacing Existing pdf")
        copy(temp_pdf, output)

def handle_process_result(result):
    if result.returncode == 0:
        return

    logging.error("Compilation Failed: %s", result.returncode)
    logging.error("Stdout: %s", result.stdout.decode())
    logging.error("Stderror: %s", result.stderr.decode())
    raise Exception()

def main():
    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    args.target = pl.Path(args.target).expanduser().resolve()


    ##-- Logging
    DISPLAY_LEVEL = logmod.DEBUG
    LOG_FILE_NAME = "log.{}".format(pathlib.Path(__file__).stem)
    LOG_FORMAT    = "%(asctime)s | %(levelname)8s | %(message)s"
    FILE_MODE     = "w"
    STREAM_TARGET = stdout

    logging         = logmod.root
    logging.setLevel(logmod.NOTSET)
    console_handler = logmod.StreamHandler(STREAM_TARGET)
    file_handler    = logmod.FileHandler(LOG_FILE_NAME, mode=FILE_MODE)

    console_handler.setLevel(DISPLAY_LEVEL)
    # console_handler.setFormatter(logmod.Formatter(LOG_FORMAT))
    file_handler.setLevel(logmod.DEBUG)
    # file_handler.setFormatter(logmod.Formatter(LOG_FORMAT))

    logging.addHandler(console_handler)
    logging.addHandler(file_handler)
    ##-- end Logging

    bib_files = retrieval.get_data_files(args.target, ".bib")

    if not args.all:
        # Collect bibs
        chosen = choice(bib_files)
        logging.info("Chosen: %s", chosen)
        process_bib(chosen, args.output)

    else:
        logging.info("Processing all bibtex files")
        for bib in bib_files:
            try:
                process_bib(bib, args.output)
                logging.info("--------------------")
            except Exception as err:
                pass



if __name__ == '__main__':
    main()
