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
from doot.task_mixins import TargetedMixin
from doit.exceptions import TaskFailed
from collections import defaultdict

batch_size  : Final= doot.config.on_fail(10, int).tool.doot.batch.size()

hash_record  : Final = doot.config.on_fail(".hashes", str).tool.doot.files.hash.record()
hash_concat  : Final = doot.config.on_fail(".all_hashes", str).tool.doot.files.hash.grouped()
hash_dups    : Final = doot.config.on_fail(".dup_hashes", str).tool.doot.files.hash.duplicates()

class HashAllFiles(globber.LazyGlobMixin, globber.DirGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin, task_mixins.BatchMixin, TargetedMixin):
    """
    ([data] -> data) For each subdir, hash all the files in it
    info
    """

    def __init__(self, name="files::hash", locs:DootLocData=None, roots=None, exts=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=exts, rec=rec)
        self.current_hashed = {}
        self.hash_record    = hash_record
        self.ext_check_fn   = lambda x: x.is_file() and x.suffix in self.exts
        if not bool(self.exts):
            self.ext_check_fn = lambda x: x.is_file()

    def set_params(self):
        return self.target_params()

    def task_detail(self, task):
        task.update({
            "targets" : [ self.hash_in_dirs ],
        })
        return task

    def filter(self, fpath):
        is_cache = fpath != pl.Path() and fpath.name[0] in "._"
        if is_cache:
            return self.control.reject

        for x in fpath.iterdir():
            if self.ext_check_fn(x):
                return self.control.accept

        return self.control.discard

    def hash_in_dirs(self):
        chunks = self.target_chunks(base=globber.LazyGlobMixin)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
            hash_file    = self.load_hashed(fpath)
            if not hash_file.exists():
                self.cmd(["touch", fpath / self.hash_record]).execute()
            self.hash_remaining(fpath)

    def load_hashed(self, fpath):
        self.current_hashed.clear()
        hash_file           = fpath / self.hash_record
        if not hash_file.exists():
            return hash_file
        hashes              = [x.split(" ") for x in hash_file.read_text().split("\n") if bool(x)]
        self.current_hashed = {" ".join(xs[1:]).strip():xs[0] for xs in hashes}
        return hash_file

    def hash_remaining(self, fpath):
        print("Hashing: ", fpath)
        dir_contents = self.glob_files(fpath)
        chunks       = self.chunk((x for x in dir_contents if str(x) not in self.current_hashed), self.args['chunkSize'])
        self.run_batches(*chunks, fn=self.batch_hash, target=hash_file)

    def batch_hash(self, data, target=None):
        assert(target is not None)
        print(f"Batch Count: {self.batch_count} (size: {len(files)})")
        # -r puts the hash first, making it easier to run `uniq` later
        act = self.cmd(["md5", "-r"] + data)
        try:
            act.execute()
        except TypeError as err:
            print(err, file=sys.stderr)
            raise TaskFailed(err)

        with open(target, 'a') as f:
            f.write("\n" + act.out)

class GroupHashes(globber.LazyGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    Concat all hash files together, to prep for duplicate detection
    """

    def __init__(self, name="files::hash.group", locs:DootLocData=None, roots=None, exts=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=exts, rec=rec)
        self.hash_record    = hash_record
        self.hash_concat    = hash_concat
        self.output         = locs.temp / self.hash_concat
        assert(self.locs.temp)

    def set_params(self):
        return self.target_params()

    def setup_detail(self, task):
        task.update({
            "actions" : [ self.cmd(["touch", self.output ])],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [ self.concat_all_hash_files ],
            "targets" : [ self.output ],
            "clean"   : True,
        })
        return task

    def filter(self, fpath):
        if fpath.name == self.hash_record:
            return self.control.accept
        return self.control.discard

    def concat_all_hash_files(self):
        chunks = self.target_chunks(base=globber.LazyGlobMixin)
        self.run_batches(*chunks)

    def batch(self, data):
        with open(self.output, 'a') as f:
            for name, fpath in data:
                f.write("\n" + fpath.read_text())

class DetectDuplicateHashes(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    sort all_hashes, and run uniq of the first n chars
    """

    def __init__(self, name="files::hash.duplicates", locs=None):
        super().__init__(name, locs)
        self.hash_collection = defaultdict(lambda: set())
        self.hash_concat     = hash_concat
        self.output          = self.locs.build / hash_dups
        assert(self.locs.temp)

    def task_detail(self, task):
        task.update({
            "actions"  : [
                self.read_hashes,
                self.identify_duplicates, #-> duplicates
                (self.write_to, [self.output, "duplicates"]),
            ],
            "file_dep" : [ self.locs.temp / self.hash_concat ],
            "targets"  : [ self.output ],
            "clean"    : True,
        })
        return task

    def read_hashes(self):
        for line in (self.locs.temp / self.hash_concat).read_text().split("\n"):
            if not bool(line):
                continue
            # split into (`hash` `filepath`)
            parts = line.strip().split(" ")
            self.hash_collection[parts[0]].add(" ".join(parts[1:]))

    def identify_duplicates(self):
        duplicates = []
        for hash_key, fnames in self.hash_collection.items():
            match len(fnames):
                case 0:
                    raise ValueError("Hash Collecion shouldn't be able to have a hash key without associated file")
                case 1:
                    continue
                case _:
                    fnames_joined = " : ".join(fnames)
                    duplicates.append(f"{hash_key} : {fnames_joined}"

        dup_str = "\n".join(duplicates)
        return {'duplicates': dup_str}

    def __sort_and_uniq(self):
        raise DeprecationWarning()
        return " ".join(["sort", self.locs.temp / self.hash_concat,
                         "|",
                         "uniq", "--all-repeated=separate",
                         # 32 : the size of the hash
                         "--check-chars=32"])
