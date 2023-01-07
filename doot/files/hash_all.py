#!/usr/bin/env python3
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

import doot
from doit.action import CmdAction
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber
from doot.utils import tasker

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

batch_size  : int       = doot.config.or_get(20).tool.doot.batch_size()

hash_record = doot.config.or_get(".hashes").tool.doot.files.hash.record()
hash_concat = doot.config.or_get(".all_hashes").tool.doot.files.hash.grouped()
hash_dups   = doot.config.or_get(".dup_hashes").tool.doot.files.hash.duplicates()

class HashAllFiles(globber.DirGlobber):
    """
    ([data] -> data) For each subdir, hash all the files in it
    info
    """

    def __init__(self, dirs:DootLocData, roots=None, exts=None):
        super().__init__("files::hash", dirs, roots or [dirs.data], exts=exts)
        self.current_hashed = {}
        self.hash_record    = hash_record
        self.ext_check_fn = lambda x: x.is_file() and x.suffix in self.exts
        if not bool(self.exts):
            self.ext_check_fn = lambda x: x.is_file()

    def filter(self, fpath):
        is_cache = fpath != pl.Path() and fpath.name[0] in "._"
        if is_cache:
            return False

        for x in fpath.iterdir():
            if self.ext_check_fn(x):
                return True

        return False

    def subtask_detail(self, fpath, task):
        task.update({
            "targets" : [ fpath / self.hash_record ],
            "actions" : [ CmdAction(["touch", fpath / self.hash_record], shell=False),
                          (self.hash_remaining, [fpath]),
                         ],
            "clean"   : True,
        })
        return task

    def load_hashed(self, fpath):
        hash_file = fpath / self.hash_record
        hashes = [x.split(" ") for x in hash_file.read_text().split("\n") if bool(x)]
        self.current_hashed = {" ".join(xs[1:]).strip():xs[0] for xs in hashes}
        return hash_file

    def hash_remaining(self, fpath):
        print("Hashing: ", fpath)
        self.reset_batch_count()

        hash_file = self.load_hashed(fpath)
        dir_contents = [x for x in fpath.iterdir() if x.stem[0] != "."]

        while bool(dir_contents):
            batch        = [x for x in dir_contents[:batch_size] if str(x) not in self.current_hashed]
            dir_contents = dir_contents[batch_size:]
            print(f"Remaining: {len(dir_contents)}")
            if not bool(batch):
                continue

            if self.run_batch([batch, hash_file]):
                return


    def batch(self, data):
        print(f"Batch Count: {self.batch_count} (size: {len(data[0])})")
        # -r puts the hash first, making it easier to run uniq
        act = CmdAction(["md5", "-r", *data[0]], shell=False)
        act.execute()
        with open(data[1], 'a') as f:
            f.write("\n" + act.out)


class GroupHashes(globber.DirGlobber):

    def __init__(self, dirs:DootLocData, roots=None, exts=None):
        super().__init__("files::hash.group", dirs, roots or [dirs.data], exts=exts)
        self.hash_record    = hash_record
        self.hash_concat    = hash_concat

    def filter(self, fpath):
        return (fpath / self.hash_record).exists()

    def setup_detail(self, task):
        task.update({
            "actions" : [CmdAction(["touch", dirs.temp / self.hash_concat], shell=False)],
            "targets" : [dirs.temp / self.hash_concat],
            "clean"   : True,
        })
        return task

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [ (self.add_to_master, [fpath / self.hash_record])],
        })
        return task

    def add_to_master(self, fpath):
        with open(self.dirs.temp / self.hash_concat, 'a') as f:
            f.write("\n" + fpath.read_text())


class DuplicateHashes(tasker.DootTasker):
    """
    sort all_hashes, and run uniq of the first n chars
    """
    def __init__(self, dirs):
        super().__init__("files::hash.duplicates", dirs)
        self.hash_concat = hash_concat

    def task_detail(self, task):
        task.update({
            "actions"  : [CmdAction(self.sort_and_uniq, save_out="duplicates"),
                          self.write_duplicates
                          ],
            "file_dep" : [self.dirs.temp / self.hash_concat],
            "targets"  : [ self.dirs.build / hash_dups ],
            "clean"    : True,
        })
        return task

    def sort_and_uniq(self):
        return " ".join(["sort", self.dirs.temp / self.hash_concat,
                         "|",
                         "uniq", "--all-repeated=separate",
                         # 32 : the size of the hash
                         "--check-chars=32"])

    def write_duplicates(self, task, targets):
        with open(targets[0], 'w') as f:
            f.write(task.values['duplicates'])
