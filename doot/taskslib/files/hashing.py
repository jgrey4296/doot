#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
import itertools
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import doot
from doot import globber, tasker, task_mixins

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
from hashlib import sha256

batch_size  : Final= doot.config.on_fail(20, int).tool.doot.batch_size()

hash_record  : Final = doot.config.on_fail(".hashes", str).tool.doot.files.hash.record()
hash_concat  : Final = doot.config.on_fail(".all_hashes", str).tool.doot.files.hash.grouped()
hash_dups    : Final = doot.config.on_fail(".dup_hashes", str).tool.doot.files.hash.duplicates()

class HashAllFiles(globber.DirGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin, task_mixins.BatchMixin):
    """
    ([data] -> data) For each subdir, hash all the files in it
    info
    """

    def __init__(self, name="files::hash", locs:DootLocData=None, roots=None, exts=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=exts, rec=rec)
        self.current_hashed = {}
        self.hash_record    = hash_record
        self.ext_check_fn = lambda x: x.is_file() and x.suffix in self.exts
        if not bool(self.exts):
            self.ext_check_fn = lambda x: x.is_file()

    def filter(self, fpath):
        is_cache = fpath != pl.Path() and fpath.name[0] in "._"
        if is_cache:
            return self.control.reject

        for x in fpath.iterdir():
            if self.ext_check_fn(x):
                return self.control.accept

        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets" : [ fpath / self.hash_record ],
            "actions" : [ self.cmd(["touch", fpath / self.hash_record]),
                          (self.hash_remaining, [fpath]),
                         ],
            "clean"   : True,
        })
        return task

    def hash_remaining(self, fpath):
        print("Hashing: ", fpath)
        hash_file    = self.load_hashed(fpath)
        dir_contents = self.glob_files(fpath)

        chunks = self.chunk((x for x in dir_contents if str(x) not in self.current_hashed),
                            batch_size)

        self.run_batches(*chunks, target=hash_file)

    def load_hashed(self, fpath):
        hash_file = fpath / self.hash_record
        hashes = [x.split(" ") for x in hash_file.read_text().split("\n") if bool(x)]
        self.current_hashed = {" ".join(xs[1:]).strip():xs[0] for xs in hashes}
        return hash_file

    def batch(self, data, target=None):
        assert(target is not None)
        print(f"Batch Count: {self.batch_count} (size: {len(files)})")
        # -r puts the hash first, making it easier to run uniq
        act = CmdAction(["md5", "-r"] + data, shell=False)
        try:
            act.execute()
        except TypeError as err:
            breakpoint(); pass
        with open(target, 'a') as f:
            f.write("\n" + act.out)

class GroupHashes(globber.DirGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """

    """

    def __init__(self, name="files::hash.group", locs:DootLocData=None, roots=None, exts=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=exts, rec=rec)
        self.hash_record    = hash_record
        self.hash_concat    = hash_concat
        assert(self.locs.temp)

    def filter(self, fpath):
        if (fpath / self.hash_record).exists():
            return self.control.accept
        return self.control.discard

    def setup_detail(self, task):
        task.update({
            "actions" : [ self.cmd(["touch", locs.temp / self.hash_concat])],
            "targets" : [locs.temp / self.hash_concat],
            "clean"   : True,
        })
        return task

    def subtask_detail(self, task, fpath=None):
        task.update({
            "actions" : [ (self.add_to_master, [fpath / self.hash_record])],
        })
        return task

    def add_to_master(self, fpath):
        with open(self.locs.temp / self.hash_concat, 'a') as f:
            f.write("\n" + fpath.read_text())

class DetectDuplicateHashes(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    sort all_hashes, and run uniq of the first n chars
    """
    def __init__(self, name="files::hash.duplicates", locs=None):
        super().__init__(name, locs)
        self.hash_concat = hash_concat
        assert(self.locs.build)
        assert(self.locs.temp)

    def task_detail(self, task):
        target = self.locs.build / hash_dups
        task.update({
            "actions"  : [ self.cmd(self.sort_and_uniq, shell=True, save="duplicates"),
                           (self.write_to, target, "duplicates"),
                          ],
            "file_dep" : [ self.locs.temp / self.hash_concat ],
            "targets"  : [ target ],
            "clean"    : True,
        })
        return task

    def sort_and_uniq(self):
        return " ".join(["sort", self.locs.temp / self.hash_concat,
                         "|",
                         "uniq", "--all-repeated=separate",
                         # 32 : the size of the hash
                         "--check-chars=32"])


