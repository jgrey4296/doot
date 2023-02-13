#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import datetime
import enum
import fileinput
import functools as ftz
import itertools as itz
import logging as logmod
import os
import pathlib as pl
import re
import shutil
import sys
import time
import types
import zipfile
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from random import randint
from time import sleep
from types import FunctionType, MethodType
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

from doit.action import CmdAction
from doit.task import Task as DoitTask
from doit.task import dict_to_task
from doit.tools import Interactive

from doot.errors import DootDirAbsent
from doot.utils.general import ForceCmd

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doit.exceptions import TaskFailed
import doot

conda_exe        = os.environ['CONDA_EXE']
sleep_notify     = doot.config.on_fail(False, bool).tool.doot.notify.sleep()
batch_size       = doot.config.on_fail(10, int).tool.doot.batch.size()
batches_max      = doot.config.on_fail(-1,    int).tool.doot.batch.max()
sleep_batch      = doot.config.on_fail(2.0,   int|float).tool.doot.batch.sleep()

zip_default_name = doot.config.on_fail("default", str).tool.doot.zip.name()
zip_overwrite    = doot.config.on_fail(False, bool).tool.doot.zip.overwrite()
zip_compression  = doot.config.on_fail("ZIP_DEFLATED", str).tool.doot.zip.compression(wrapper=lambda x: getattr(zipfile, x))
zip_level        = doot.config.on_fail(4, int).tool.doot.zip.level()

class BatchMixin:
    """
    A Mixin to enable running batches of processing with
    some sleep time

    'run_batches' controls batching bookkeeping,
    'batch' is the actual action
    """

    batch_count       = 0

    def run_batches(self, *batches, reset=True, fn=None, **kwargs):
        """
        handles batch bookkeeping

        defaults to self.batch, but can pass in a function
        """
        if reset:
            self._reset_batch_count()
        fn = fn or self.batch

        result = []
        for data in batches:
            match data:
                case [*items]:
                    batch_data = [x for x in items if x is not None]
                    if not bool(batch_data):
                        continue
                    self.log(f"Batch: {self.batch_count} : ({len(batch_data)})")
                case _:
                    batch_data = data

            batch_result =  fn(batch_data, **kwargs)
            match batch_result:
                case None:
                    pass
                case list():
                    result += batch_result
                case set():
                    result += list(batch_result)
                case _:
                    result.append(batch_result)

            self.batch_count += 1
            if -1 < batches_max < self.batch_count:
                self.log("Max Batch Hit")
                return
            if sleep_notify:
                self.log("Sleep Batch")
            sleep(sleep_batch)

        return result

    def batch(self, data, **kwargs):
        """ Override to implement what a batch does """
        raise NotImplementedError()

    def chunk(self, iterable, n=batch_size, *, incomplete='fill', fillvalue=None):
        """Collect data into non-overlapping fixed-length chunks or blocks
        from https://docs.python.org/3/library/itertools.html
         grouper('ABCDEFG', 3, fillvalue='x') --> ABC DEF Gxx
         grouper('ABCDEFG', 3, incomplete='strict') --> ABC DEF ValueError
         grouper('ABCDEFG', 3, incomplete='ignore') --> ABC DEF
        """
        args = [iter(iterable)] * n
        if incomplete == 'fill':
            return itz.zip_longest(*args, fillvalue=fillvalue)
        if incomplete == 'strict':
            return zip(*args, strict=True)
        if incomplete == 'ignore':
            return zip(*args)
        else:
            raise ValueError('Expected fill, strict, or ignore')

    def _reset_batch_count(self):
        self.batch_count = 0

class CommanderMixin:

    def cmd(self, cmd:list|callable, *args, shell=False, save=None, **kwargs):
        logging.debug("Cmd: %s Args: %s kwargs: %s", cmd, args, kwargs)
        match cmd:
            case FunctionType() | MethodType():
                action = (cmd, list(args), kwargs)
            case str():
                action = [cmd, *args]
            case list():
                assert(not bool(args))
                assert(not bool(kwargs))
                action = cmd
            case _:
                raise TypeError("Unexpected action form: ", cmd)

        return CmdAction(action, shell=shell, save_out=save)

    def force(self, cmd:list|callable, *args, handler=None, shell=False, save=None, **kwargs):
        logging.debug("Forcing Cmd: %s Args: %s kwargs: %s", cmd, args, kwargs)
        match cmd:
            case FunctionType() | MethodType():
                action = (cmd, list(args), kwargs)
            case list():
                assert(not bool(args))
                assert(not bool(kwargs))
                action = cmd
            case _:
                raise TypeError("Unexpected action form: ", cmd)

        return ForceCmd(action, shell=shell, handler=handler, save_out=save)

    def shell(self, cmd:list|callable, *args, **kwargs):
        return self.cmd(cmd, *args, shell=True, **kwargs)

    def interact(self, cmd:list|callable, *args, save=None, **kwargs):
        match cmd:
            case FunctionType():
                action = (cmd, list(args), kwargs)
            case list():
                assert(not bool(args))
                assert(not bool(kwargs))
                action = cmd
            case _:
                raise TypeError("Unexpected action form: ", cmd)
        return Interactive(action, shell=False, save_out=save)

    def regain_focus(self, prog="iTerm"):
        """
        Applescript command to regain focus for if you lose it
        """
        return self.cmd(["osascript", "-e", f"tell application \"{prog}\"", "-e", "activate", "-e", "end tell"])

    def say(self, *text, voice="Moira"):
        cmd = ["say", "-v", voice, "-r", "50"]
        cmd += text
        return CmdAction(cmd, shell=False)

    def in_conda(self, env, *args):
        return CmdAction([conda_exe, "run", "-n", env, *args], shell=False)

class FilerMixin:

    def rmglob(self, root:pl.Path, *args):
        for x in args:
            for y in root.glob(x):
                y.unlink()

    def rmfiles(self, *args):
        for x in args:
            x.unlink(missing_ok=True)

    def rmdirs(self, *locs:pl.Path):
        logging.debug("Removing Directories: %s", locs)
        for target in locs:
            if not target.exists():
                logging.warning("Non-existent rmdir: %s", target)
                continue
            shutil.rmtree(target)

    def mkdirs(self, *locs:pl.Path):
        for target in locs:
            if not target.exists():
                logging.debug("Making Directory: %s", target)
                target.mkdir(parents=True, exist_ok=True)

    def write_to(self, fpath, key:str|list[str], task, sep=None):
        if sep is None:
            sep = "\n--------------------\n"
        match key:
            case str():
                value = task.values[key]
            case [*strs]:
                value = sep.join([task.values[x] for x in key])

        fpath.write_text(value)

    def append_to(self, fpath, key:str|list[str], task, sep=None):
        if sep is None:
            sep = "\n--------------------\n"

        match key:
            case str():
                value = task.values[key]
            case [*strs]:
                value = sep.join([task.values[x] for x in key])

        with open(fpath, 'a') as f:
            f.write(value)

    def move_to(self, fpath:pl.Path, *args, fn=None):
        """
        Move *args to fpath, with fn as the naming strategy
        only overwrite if is_backup is true
        if fpath is a file, only one arg is allowed
        """
        # Set the naming strategy:
        assert(fpath.parent.exists())
        overwrite = True
        match fn:
            case FunctionType() | MethodType():
                pass
            case "overwrite":
                fn = lambda d, x: d / x.name
            case "backup":
                fn = lambda d, x: d / f"{x.parent.name}_{x.name}_backup"
            case "file":
                assert(not fpath.is_dir())
                fn = lambda d, x: d
            case _:
                overwrite = False
                fn = lambda d, x: d / x.name

        # Then do the move
        for x in args:
            target_path = fn(fpath, x)
            if not overwrite and target_name.exists():
                 logging.warning("Not Moving: %s -> %s", x, target_name)
                 continue
            logging.debug("Renaming: %s -> %s", x, target_path)
            x.rename(target_path)

    def copy_to(self, fpath ,*args, fn=None):
        assert(fpath.parent.exists())
        overwrite = True
        match fn:
            case FunctionType() | MethodType():
                pass
            case "overwrite":
                fn = lambda d, x: d / x.name
            case "backup":
                fn = lambda d, x: d / f"{x.parent.name}_{x.name}_backup"
            case "file":
                assert(not fpath.is_dir())
                fn = lambda d, x: d
            case _:
                overwrite = False
                fn = lambda d, x: d / x.name

        for x in args:
            target_name = fn(fpath, x)
            if not overwrite and target_name.exists():
                logging.warning("File Exists already: %s -> %s", x, target_name)
                continue
            match x.is_file():
                case True:
                    shutil.copy(x, target_name)
                case False:
                    shutil.copytree(x, target_name, dirs_exist_ok=True)

class ActionsMixin(CommanderMixin, FilerMixin):

    def get_uuids(self, *args):
        raise NotImplementedError()

    def edit_by_line(self, files:list[pl.Path], fn, inplace=True):
        for line in fileinput(files=files, inplace=inplace):
            fn(line)

class ZipperMixin:
    zip_name       = zip_default_name
    zip_overwrite  = zip_overwrite
    zip_root       = None
    compression    = zip_compression
    compress_level = zip_level

    def zip_set_root(self, fpath):
        self.zip_root = fpath

    def zip_create(self, fpath):
        assert(fpath.suffix== ".zip")
        if self.zip_overwrite and fpath.exists():
            fpath.unlink()
        elif fpath.exists():
            return

        logging.info("Creating Zip File: %s", fpath)
        now = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
        record_str = f"Zip File created at {now} for doot task: {self.base}"

        with zipfile.ZipFile(fpath, mode='w', compression=self.compression, compresslevel=self.compress_level, allowZip64=True ) as targ:
            targ.writestr(".taskrecord", record_str)

    def zip_add_paths(self, fpath, *args):
        """
        Add specific files to the zip
        """
        logging.info("Adding to Zipfile: %s : %s", fpath, args)
        assert(fpath.suffix == ".zip")
        root = self.zip_root or pl.Path()
        paths = [pl.Path(x) for x in args]
        with zipfile.ZipFile(fpath, mode='a',
                             compression=self.compression, compresslevel=self.compress_level,
                             allowZip64=True ) as targ:
            for file_to_add in paths:
                try:
                    relpath = file_to_add.relative_to(root)
                    attempts = 0
                    write_as = relpath
                    while str(write_as) in targ.namelist():
                        if attempts > 10:
                            logging.warning(f"Couldn't settle on a de-duplicated name for: {file_to_add}")
                            break
                        logging.debug(f"Attempted Name Duplication: {relpath}", file=sys.stderr)
                        write_as = relpath.with_stem(f"{relpath.stem}_{hex(randint(1,100))}")
                        attempts += 1

                    targ.write(str(file_to_add), write_as)

                except ValueError:
                    relpath = root / pl.Path(file_to_add).name
                except FileNotFoundError as err:
                    logging.warning(f"Adding File to Zip {fpath} failed: {err}", file=sys.stderr)

    def zip_globs(self, fpath, *globs):
        """
        Add files chosen by globs to the zip, relative to the cwd
        """
        logging.debug(f"Zip Globbing: %s : %s", fpath, globs)
        assert(fpath.suffix == ".zip")
        cwd  = pl.Path()
        root = self.zip_root or cwd
        with zipfile.ZipFile(fpath, mode='a',
                             compression=self.compression, compresslevel=self.compress_level,
                             allowZip64=True) as targ:
            for glob in globs:
                result = list(cwd.glob(glob))
                logging.info(f"Globbed: {cwd}[{glob}] : {len(result)}")
                for dep in result:
                    try:
                        if dep.stem[0] == ".":
                            continue
                        relpath = pl.Path(dep).relative_to(root)
                        targ.write(str(dep), relpath)
                    except ValueError:
                        relpath = root / pl.Path(dep).name
                    except FileNotFoundError as err:
                        logging.warning(f"Adding File to Zip {fpath} failed: {err}", file=sys.stderr)

    def zip_add_str(self, fpath, fname, text:str):
        assert(fpath.suffix == ".zip")
        with zipfile.ZipFile(fpath, mode='a',
                             compression=self.compression, compresslevel=self.compress_level,
                             allowZip64=True) as targ:
            assert(fname not in targ.namelist())
            targ.writestr(fname, text)

class TargetedMixin:
    """
    For Quickly making a task have cli args to control batching
    """

    def target_params(self) -> list:
        return [
            {"name": "target", "short": "t", "type": str, "default": None},
            {"name": "all", "long": "all", "type": bool, "default": False},
            {"name": "chunkSize", "long": "chunkSize", "type": int, "default": batch_size},
        ]

    def target_chunks(self, *, root=None, base=None):
        match self.args, root:
            case {'all': True}, None:
                globbed = super(base, self).glob_all()
                chunks  = self.chunk(globbed, self.args['chunkSize'])
                return chunks
            case {'all': True}, _:
                globbed = [(x.name, x) for x in self.glob_target(root)]
                chunks  = self.chunk(globbed, self.args['chunkSize'])
                return chunks
            case {'target': None}, None:
                raise Exception("No Target Specified")
            case {'target': None}, _:
                fpath  = root
            case {'target': targ}, None:
                fpath = self.locs.root / targ
            case _, _:
                raise Exception("No Target Specified")

        if not fpath.exists():
            raise Exception("Target Doesn't Exist")

        globbed = [(x.name, x) for x in self.glob_target(fpath)]
        logging.debug("Generating for: %s", [x[0] for x in globbed])
        chunks  = self.chunk(globbed, self.args['chunkSize'])
        return chunks
