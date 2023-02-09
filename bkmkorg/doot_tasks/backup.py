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

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot
from doot import globber, task_mixins
from doot.taskslib.files.backup import BackupTask

class BackupBibtexLib(BackupTask):

    def __init__(self, name="backup::pdf", locs=None):
        super().__init__(name, locs, [locs.pdfs], output=locs.pdf_backup)

class BackupBibtexSummary(BackupTask):

    def __init__(self, name="backup::summary", locs=None):
        super().__init__(name, locs, [locs.pdf_summary], output=locs.pdf_summary_backup)

class BackupTwitterLib(BackupTask):

    def __init__(self, name="backup::twitter", locs=None):
        super().__init__(name, locs, [locs.thread_library], output=locs.thread_backup)


class TwitterArchive(globber.LazyGlobMixin, globber.DootEagerGlobber, task_mixins.BatchMixin, task_mixins.ActionsMixin, task_mixins.ZipperMixin):
    """
    Zip json data for users

    Get Threads -> components,
    combine,
    add to archive.zip in base user's library directory
    """

    def __init__(self, name="twitter::zip", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.threads], rec=rec, exts=exts or [".json"])
        self.group_reg     = re.compile(r"^[a-zA-Z]")
        self.output         = None
        self.thread_data    = None
        self.component_data = None
        self.locs.ensure("thread_library")

    def task_detail(self, task, fpath):
        task.update({
            "actions": [ self.archive_all ],
        })
        return task

    def archive_all(self):
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        chunks = self.chunk(globbed)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
            self.thread_data    = json.loads(fpath.read_text())
            self.component_data = json.loads(pl.Path(task.values['component']).read_text())
            component           = self.thread_data['component']
            base_user           = self.thread_data['base_user']
            target_path         = self.calc_target_path(base_user)
            self.add_to_user_archive(target_path, base_user, component)

    def calc_target_path(self, base_user):
        group = "group_symbols"
        if re.match(r"^[a-zA-Z]", base_user):
            group = f"group_{base_user[0]}"

        target_path = self.locs.thread_library / group / base_user / "archive.zip"
        return target_path

    def add_to_user_archive(self, target_path, base_user, component):
        as_json = json.dumps({"thread": self.thread_data, "component": self.component_data})
        json_name = pl.Path(component).name

        if not target_path.exists():
            self.zip_create(target_path)

        self.zip_add_str(target_path, json_name, as_json)
