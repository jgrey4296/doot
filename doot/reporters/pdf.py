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
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import doot
from doot import globber, tasker
from doot.mixins.batch import BatchMixin
from doot.mixins.bibtex import clean as bib_clean
from doot.mixins.bibtex import utils as bib_utils
from doot.mixins.bibtex.load_save import BibLoadSaveMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.pdf import PdfMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.web import WebMixin
from doot.tasker import DootTasker
from doot.tasks.files.backup import BackupTask
from doot.utils.formats.timelinefile import TimelineFile
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

min_tag_timeline     : Final[int] = doot.config.on_fail(10, int).bibtex.min_timeline()
stub_exts            : Final[list] = doot.config.on_fail([".pdf", ".epub", ".djvu", ".ps"], list).bibtex.stub_exts()
clean_in_place       : Final[bool] = doot.config.on_fail(False, bool).bibtex.clean_in_place()
wayback_wait         : Final[int] = doot.config.on_fail(10, int).bibtex.wayback_wait()
acceptible_responses : Final[list] = doot.config.on_fail(["200"], list).bibtex.accept_wayback()
ENT_const            : Final[str] = 'ENTRYTYPE'

class PdfLibSummary(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, PdfMixin):
    """
    Compile the first n pages of each pdf in a decade together
    """

    def __init__(self, name="report::pdflib", locs=None, roots=None, output=None):
        super().__init__(name, locs, roots or [locs.pdfs], rec=True)
        self.output = output or locs.pdf_summary

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and fpath.name.isdigit():
            return self.globc.keep
        return self.globc.discard

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.summarise_year, [fpath]) ],
        })
        return task

    def summarise_year(self, fpath):
        pdfs = fpath.rglob("*.pdf")
        self.pdf_summary(pdfs, output=self.output)
