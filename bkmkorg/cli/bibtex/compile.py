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

from bkmkorg.files import collect

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
parser.add_argument('--timeout', default=3, help="timeout in minutes")
parser.add_argument('--all', action="store_true")
parser.add_argument("-v", "--verbose",     action='count', help="increase verbosity of logging (repeatable)")
parser.add_argument('--logfilter')
##-- end argparse


def process_bib(bib_target, output, *, timeout=3):
    timeout *= 60 # convert minutes to seconds

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

        logging.info("First Pass: %s", temp_tex.stem)
        result = subprocess.run(["pdflatex", temp_tex.stem],
                                capture_output=True,
                                cwd=str(temp_dir_p),
                                timeout=timeout)
        handle_process_result("first", temp_tex.stem, result)
        logging.info("Bibtex Pass")
        result = subprocess.run(["bibtex", temp_tex.stem],
                                capture_output=True,
                                cwd=str(temp_dir_p),
                                timeout=timeout)
        handle_process_result("bib", temp_tex.stem, result)
        logging.info("Second Pass")
        result = subprocess.run(["pdflatex", temp_tex.stem],
                                capture_output=True,
                                cwd=str(temp_dir_p),
                                timeout=timeout)
        handle_process_result("second", temp_tex.stem, result)
        logging.info("Third Pass")
        result = subprocess.run(["pdflatex", temp_tex.stem],
                                capture_output=True,
                                cwd=str(temp_dir_p),
                                timeout=timeout)
        handle_process_result("third", temp_tex.stem, result)

        # move to output
        assert(temp_pdf.exists())
        if (output / temp_pdf.name).exists():
            logging.info("Replacing Existing pdf")
        copy(temp_pdf, output)

def handle_process_result(pass_str, name, result):
    if result.returncode == 0:
        return

    raise Exception(f"{pass_str} : {name}",
                    result.returncode,
                    result.stdout.decode(),
                    result.stderr.decode())

def main():
    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    args.target = pl.Path(args.target).expanduser().resolve()


    ##-- Logging
    DISPLAY_LEVEL = logmod.WARNING
    LOG_FILE_NAME = "log.{}".format(pathlib.Path(__file__).stem)
    LOG_FORMAT    = "%(asctime)s | %(levelname)8s | %(message)s"
    FILE_MODE     = "w"
    STREAM_TARGET = stdout

    logging         = logmod.root
    logging.setLevel(logmod.NOTSET)
    console_handler = logmod.StreamHandler(STREAM_TARGET)
    file_handler    = logmod.FileHandler(LOG_FILE_NAME, mode=FILE_MODE)

    verbosity = max(logmod.DEBUG, logmod.WARNING - (10 * (args.verbose or 0)))
    console_handler.setLevel(verbosity)
    if args.logfilter:
        console_handler.addFilter(logmod.Filter(args.logfilter))

    file_handler.setLevel(logmod.DEBUG)

    logging.addHandler(console_handler)
    logging.addHandler(file_handler)
    ##-- end Logging

    bib_files = collect.get_data_files(args.target, ".bib")

    if not args.all:
        # Collect bibs
        chosen = choice(bib_files)
        logging.info("Chosen: %s", chosen)
        process_bib(chosen, args.output, timeout=args.timeout)

    else:
        logging.info("Processing all bibtex files")
        for bib in bib_files:
            try:
                process_bib(bib, args.output, timeout=args.timeout)
                logging.info("--------------------")
            except subprocess.TimeoutExpired as err:
                logging.error("---- Process Timed out: %s", bib)

            except Exception as err:
                logging.error("---- Exception Occurred for: %s : %s", bib, err.args[0])
                logging.error(err)



##-- ifmain
if __name__ == '__main__':
    main()

##-- end ifmain
