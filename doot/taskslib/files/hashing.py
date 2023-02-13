#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
import itertools
import functools
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
import fileinput
import re

batch_size   : Final= doot.config.on_fail(10, int).tool.doot.batch.size()

hash_record  : Final = doot.config.on_fail(".hashes", str).tool.doot.files.hash.record()
hash_concat  : Final = doot.config.on_fail(".all_hashes", str).tool.doot.files.hash.grouped()
hash_dups    : Final = doot.config.on_fail(".dup_hashes", str).tool.doot.files.hash.duplicates()

class HashAllFiles(globber.LazyGlobMixin, globber.DirGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin, task_mixins.BatchMixin, TargetedMixin):
    """
    ([data] -> data) For each subdir, hash all the files in it to .hashes

    """

    def __init__(self, name="files::hash", locs:DootLocData=None, roots=None, exts=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=exts, rec=rec)
        self.current_hashed = {}
        self.hash_record    = hash_record
        self.check_fn       = lambda x: x.is_file() and x.name[0] != "."

    def clean(self, task):
        for root in self.roots:
            for fpath in root.rglob(self.hash_record):
                logging.info("Would Delete: %s", fpath)

    def set_params(self):
        return self.target_params()

    def task_detail(self, task):
        task.update({
            "actions" : [ self.hash_in_dirs ],
        })
        return task

    def filter(self, fpath):
        is_cache = fpath != pl.Path() and fpath.name[0] in "._"
        if is_cache:
            return self.control.reject

        for x in fpath.iterdir():
            if self.check_fn(x):
                return self.control.accept

        return self.control.discard

    def hash_in_dirs(self):
        """
        Glob for applicable directories
        """
        chunks = self.target_chunks(base=globber.LazyGlobMixin)
        self.run_batches(*chunks)

    def batch(self, data):
        """
        For each applicable directory, hash files as necessary
        """
        for name, fpath in data:
            logging.info("Processing: %s", fpath)
            dir_contents = self.glob_files(fpath, rec=False, fn=self.check_fn)
            if not bool(dir_contents):
                continue
            logging.debug("%s Dir Contents: %s", fpath, dir_contents)

            hash_file    = self.load_hashed(fpath)
            if not hash_file.exists():
                self.cmd(["touch", fpath / self.hash_record]).execute()

            chunks       = self.chunk((x for x in dir_contents if str(x) not in self.current_hashed), self.args['chunkSize'])
            self.run_batches(*chunks, fn=self.batch_hash, target=fpath / self.hash_record)

    def load_hashed(self, fpath):
        self.current_hashed.clear()
        hash_file           = fpath / self.hash_record
        if not hash_file.exists():
            return hash_file
        hashes              = [x.split(" ") for x in hash_file.read_text().split("\n") if bool(x)]
        self.current_hashed = {" ".join(xs[1:]).strip():xs[0] for xs in hashes}
        return hash_file

    def batch_hash(self, data, target=None):
        assert(target is not None)
        try:
            fpaths = [x for x in data if x.name != self.hash_record]
            if not bool(fpaths):
                return

            logging.info("Batch Count: %s (size: %s)", self.batch_count, len(data))
            # -r puts the hash first, making it easier to run `uniq` later
            act = self.cmd(["md5", "-r"] + fpaths)
            act.execute()
        except TypeError as err:
            print(err, file=sys.stderr)
            raise err

        with open(target, 'a') as f:
            f.write("\n" + act.out)

class GroupHashes(globber.LazyGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin, TargetedMixin, task_mixins.BatchMixin):
    """
    Concat all .hashes files together, to prep for duplicate detection
    """

    def __init__(self, name="files::hash.group", locs:DootLocData=None, roots=None, exts=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=exts, rec=rec)
        self.hash_record    = hash_record
        self.hash_concat    = hash_concat
        self.output         = locs.temp / self.hash_concat

    def set_params(self):
        return self.target_params()

    def setup_detail(self, task):
        task.update({
            "actions" : [
                (self.rmfiles, [self.output]),
                self.cmd(["touch", self.output ]),
            ],
        })
        return task

    def is_current(self, task):
        match self.args:
            case {'all': False, 'target': None}:
                return True
            case _:
                return False

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
        logging.debug("Hash Concat: %s", data)
        with open(self.output, 'a') as f:
            for name, fpath in data:
                f.write("\n" + fpath.read_text())

class DetectDuplicateHashes(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    sort all_hashes, and run uniq of the first n chars
    """

    def __init__(self, name="files::hash.dups", locs=None):
        super().__init__(name, locs)
        self.hash_collection = defaultdict(lambda: set())
        self.hash_concat     = self.locs.temp / hash_concat
        self.output          = self.locs.build / hash_dups
        self.locs.ensure("temp")

    def is_current(self, task):
        return False

    def task_detail(self, task):
        task.update({
            "actions"  : [
                self.read_hashes,
                self.identify_duplicates, #-> duplicates
                (self.write_to, [self.output, "duplicates"]),
            ],
            "file_dep" : [ self.hash_concat ],
            "targets"  : [ self.output ],
            "clean"    : True,
        })
        return task

    def read_hashes(self):
        for line in self.hash_concat.read_text().split("\n"):
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
                    fnames_joined = " : ".join(sorted(fnames))
                    duplicates.append(f"{hash_key} : {fnames_joined}")

        dup_str = "\n".join(duplicates)
        return {'duplicates': dup_str}

    def __sort_and_uniq(self):
        cmd = " ".join(["sort", self.hash_concat,
                         "|",
                         "uniq", "--all-repeated=separate",
                         # 32 : the size of the hash
                         "--check-chars=32"])

        raise DeprecationWarning()

class DeleteDuplicates(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    Delete duplicates, using a set heuristic

    heuristics:
    delete  oldest/newest
    prefer  locations [xs]
    protect locations [ys]
    """

    def __init__(self, name="files::dups.rm", locs=None):
        super().__init__(name, locs)
        self.target = self.locs.build / hash_dups
        self.num_re = re.compile(r"\(\d+\)$")
        self.output = self.locs.build / "to_delete"
        self.delete_log = []

    def set_params(self):
        return [
            {"name": "samedir", "short": "s", "type": bool, "default": False},
            {"name": "root", "long": "root", "type": pl.Path, "default": self.locs.data },

            {"name": "prefer", "long": "pref", "type": str, "default": None},
        ]

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.delete_duplicates,
                self.write_delete_log,
            ],
        })
        return task

    def delete_duplicates(self):
        if not self.output.exists():
            self.output.mkdir()

        process = lambda xs: None
        match self.args:
            case { "samedir": True}:
                process = self.delete_in_same_dir
            case { "prefer" : pair} if pair is not None:
                prefs = pair.split("<")
                process = functools.partial(self.delete_preferring, prefs)
            case _:
                logging.info("No Applicable heuristic selected")
                return

        for line in self.target.read_text().split("\n"):
            if not bool(line.strip()):
                continue

            parts = line.split(" : ")
            if len(parts) < 3:
                raise Exception("Bad duplicate line: ", line)

            fpaths   = [pl.Path(x.strip()) for x in parts[1:]]
            suitable = [x for x in fpaths if x.is_relative_to(self.args['root'])]
            if not bool(suitable):
                continue

            to_delete = process(suitable)
            self.queue_delete(to_delete)

    def delete_in_same_dir(self, dups):
        parent_dirs = defaultdict(lambda: set())
        for fpath in dups:
            parent_dirs[str(fpath.parent)].add(fpath)

        results = []
        for group in parent_dirs.values():
            if len(group) < 2:
                continue

            available = [x for x in group if self.num_re.search(x.stem)]
            if len(available) >= len(group):
                continue


            results += available

        return results

    def delete_preferring(self, prefs, dups):
        pref_dict            = {y:x for x,y in enumerate(prefs, 1)}
        matching             = [(x,pref_dict.get(x.parent.name, -10)) for x in dups]
        only_preferences     = [x for x in matching if x[1] > 0]
        sorted_by_preference = sorted(only_preferences, key=lambda x: x[1])
        to_delete            = sorted_by_preference[:-1]

        if not bool(to_delete):
            return []

        return [x[0] for x in to_delete]


    def queue_delete(self, delete_list):
        for fpath in delete_list:
            try:
                fpath.rename(self.output / fpath.name)
            except FileNotFoundError:
                logging.info("Not Found for deletion: %s", fpath)

        self.delete_log.append(delete_list)

    def write_delete_log(self):
        with open(self.locs.build / "delete.log", 'w') as f:
            for line in self.delete_log:
                line_str = " ".join([str(x) for x in line])
                print(line_str, file=f)

class RemoveMissingHashes(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    Remove hashes in hash files that dont exist anymore
    """

    def __init__(self, name="files::hash.clean", locs=None):
        super().__init__(name, locs)
        self.hash_record = hash_record

    def task_detail(self, task):
        task.update({
            "actions" : [ self.clean_hashes ]
        })
        return task

    def clean_hashes(self):
        globbed = list(self.locs.data.rglob(self.hash_record))
        if not bool(globbed):
            return

        for line in fileinput.input(files=globbed, inplace=True):
            if not bool(line.strip()):
                continue

            fpath = pl.Path(" ".join(line.strip().split(" ")[1:]))
            if not fpath.exists():
                continue
            if fpath.name[0] == ".":
                continue

            print(line.strip())
