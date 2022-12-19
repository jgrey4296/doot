#/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref
import datetime

from doit.action import CmdAction

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

pdf_dir = build_dir / "pdfs"

##-- dir check
check_pdfs = CheckDir(paths=[pdf_dir], name="pdfs", task_dep=["_checkdir::build"],)
##-- end dir check

class ImgConvertTask:
    """
    Combine globbed images into a single pdf file
    """

    def __init__(self, target, **, paths=None, globs=None, name="default", date=False, **kwargs):
        self.create_doit_tasks = self.build
        self.paths             = [pl.Path(x) for x in paths]
        self.globs             = globs or []
        self.kwargs            = kwargs
        self.default_spec      = { "basename" : f"img.convert::{name}" }
        self.date              = date
        self.target_stem       = pl.Path(target).stem
        match date:
            case False:
                self.target : pl.Path = pdf_dir / target
            case True:
                now                   = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
                dated_target          = f"{self.target_stem}-{now}.pdf"
                self.target : pl.Path = pdf_dir / dated_target
            case str():
                now                   = datetime.datetime.strftime(datetime.datetime.now(), date)
                dated_target          = f"{self._target_stem}-{now}.pdf"
                self.target : pl.Path = pdf_dir / dated_target


    def get_images(self):
        pass

    def convert_images(self):
        # convert ? -alpha off ./temp/`?`
        # mogrify -orient bottom-left ?
        # img2pdf --output `?`.pdf --pagesize A4 --auto-orient ?
        pass

    def combine_images(self):
        # pdftk * cat output diagrams.pdf
        pass

    def clean_pdfs(self):
        pdf_base = pdf_dir
        print(f"Cleaning {pdf_base}/{self.target_stem}*.pdf")
        for zipf in pdf_base.glob(f"{self.target_stem}*.pdf"):
            zipf.unlink()


    def build(self) -> dict:
        task_desc = self.default_spec.copy()
        task_desc.update(self.kwargs)
        task_desc.update({
            "actions"  : [ self.get_images, self.convert_images, self.combine_images ],
            "targets"  : [ self.target ],
            "file_dep" :  self.paths,
            "uptodate" : [ False ],
            "clean"    : [ self.clean_pdfs ],
        })
        return task_desc


