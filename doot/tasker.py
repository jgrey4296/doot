#!/usr/bin/env python3
"""
Utility classes for building tasks with a bit of structure
"""
##-- imports
from __future__ import annotations

import sys
from time import sleep
import abc
import logging as logmod
import itertools
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Final)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import datetime
import fileinput
from types import FunctionType, MethodType
import shutil
from doit.action import CmdAction
from doit.tools import Interactive
from doit.task import Task as DoitTask
from doit.task import dict_to_task
from doot.errors import DootDirAbsent
from doot.utils.general import ForceCmd
import zipfile
from random import randint

class DootTasker:
    """ Util Class for building single tasks

    """
    sleep_subtask : ClassVar[Final[float]]
    sleep_batch   : ClassVar[Final[float]]
    sleep_notify  : ClassVar[Final[bool]]
    batches_max   : ClassVar[Final[int]]

    @staticmethod
    def set_defaults(config:TomlAccess):
        DootTasker.sleep_subtask = config.on_fail(2.0,   int|float).tool.doot.sleep_subtask()
        DootTasker.sleep_batch   = config.on_fail(2.0,   int|float).tool.doot.sleep_batch()
        DootTasker.batches_max   = config.on_fail(-1,    int).tool.doot.batches_max()
        DootTasker.sleep_notify  = config.on_fail(False, bool).tool.doot.sleep_notify()

    def __init__(self, base:str, locs:DootLocData=None, output=None):
        assert(base is not None)
        assert(locs is not None or locs is False), locs

        # Wrap in a lambda because MethodType does not behave as we need it to
        self.create_doit_tasks = lambda *a, **kw: self._build(*a, **kw)
        self.create_doit_tasks.__dict__['basename'] = base
        params = self.set_params()
        if bool(params):
            self.create_doit_tasks.__dict__['_task_creator_params'] = params

        self.base         = base
        self.locs         = locs
        self.args         = {}
        self._setup_name  = None
        self.active_setup = False
        self.output       = None

    def set_params(self) -> list:
        return []

    def default_task(self) -> dict:
        return dict([("name"     , self.base),
                     ("meta"     , self.default_meta()),
                     ("actions"  , list()),
                     ("task_dep" , list()),
                     ("setup"    , list()),
                     ("doc"      , self.doc),
                     ("uptodate" , [self.is_current]),
                     ("clean"    , [self.clean]),
                     ])

    def default_meta(self) -> dict:
        meta = dict()
        return meta

    @property
    def doc(self):
        try:
            split_doc = [x for x in self.__class__.__doc__.split("\n") if bool(x)]
            return ":: " + split_doc[0].strip() if bool(split_doc) else ""
        except AttributeError:
            return ":: "

    def is_current(self, task:DoitTask):
        return False

    def clean(self, task:DoitTask):
        return

    def setup_detail(self, task:dict) -> None|dict:
        return task

    def task_detail(self, task:dict) -> dict:
        return task

    @property
    def setup_name(self):
        if self._setup_name is not None:
            return self._setup_name

        private = "_" if self.base[0] != "_" else ""
        full = f"{private}{self.base}:setup"
        return full

    def _build_setup(self) -> DoitTask:
        """
        Build a pre-task that every subtask depends on
        """
        try:
            task_spec             = self.default_task()
            task_spec['name']     = self.setup_name
            if self.locs is not None and not isinstance(self.locs, bool):
                task_spec['setup'] = [ self.locs.checker ]

            match self.setup_detail(task_spec):
                case None:
                    return None
                case str() as sname:
                    self._setup_name = sname
                    return None
                case dict() as val:
                    self.active_setup = True
                    return dict_to_task(val)
                case _ as val:
                    logging.warning("Setup Detail Returned an unexpected value: ", val)
        except DootDirAbsent:
            return None

    def _build_task(self):
        logging.info("Building Task for: %s", self.base)
        task                     = self.default_task()
        maybe_task : None | dict = self.task_detail(task)
        if maybe_task is None:
            return None
        if self.active_setup:
            maybe_task['setup'] += [self.setup_name]

        full_task = dict_to_task(maybe_task)
        return full_task

    def _build(self, **kwargs):
        try:
            self.args.update(kwargs)
            setup_task = self._build_setup()
            task       = self._build_task()

            if task is not None:
                yield task
            else:
                return None
            if setup_task is not None:
                yield setup_task

        except Exception as err:
            print("ERROR: Task Creation Failure: ", err, file=sys.stderr)
            print("ERROR: Task was: ", self.base, file=sys.stderr)
            exit(1)

class DootSubtasker(DootTasker):
    """ Extends DootTasker to make subtasks

    add a name in task_detail to run actions after all subtasks are finished
    """

    def __init__(self, base:str, locs, **kwargs):
        super().__init__(base, locs, **kwargs)

    def subtask_detail(self, task, **kwargs) -> None|dict:
        return task

    def _build_task(self):
        task = super()._build_task()
        task.has_subtask = True
        task.update_deps({'task_dep': [f"{self.base}:*"] })
        if self.active_setup:
            task.update_deps({"task_dep": [self.setup_name]})
        return task

    def _build_subtask(self, n:int, uname, **kwargs):
        try:
            spec_doc  = self.doc + f" : {kwargs}"
            task_spec = self.default_task()
            task_spec.update({"name"     : f"{uname}",
                              "doc"      : spec_doc,
                              })
            task_spec['meta'].update({ "n" : n })
            task = self.subtask_detail(task_spec, **kwargs)
            if task is None:
                return

            if self.active_setup:
                task['setup'] += [self.setup_name]

            if bool(self.sleep_subtask):
                task['actions'].append(self._sleep_subtask)

            return task
        except DootDirAbsent:
            return None

    def _build_subs(self):
        raise NotImplementedError()

    def _build(self, **kwargs):
        try:
            self.args.update(kwargs)
            setup_task = self._build_setup()
            task       = self._build_task()
            subtasks   = self._build_subs()

            if task is None:
                return None
            yield task

            if setup_task is not None:
                yield setup_task

            for x in subtasks:
                yield x

        except Exception as err:
            print("ERROR: Task Creation Failure: ", err, file=sys.stderr)
            print("ERROR: Task was: ", self.base, file=sys.stderr)
            exit(1)

    def _sleep_subtask(self):
        if self.sleep_notify:
            print("Sleep Subtask")
        sleep(self.sleep_subtask)

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
                    print(f"Batch: {self.batch_count} : ({len(batch_data)})")
                case _:
                    batch_data = data

            result.append(fn(batch_data, **kwargs))

            self.batch_count += 1
            if -1 < self.batches_max < self.batch_count:
                print("Max Batch Hit")
                return
            if self.sleep_notify:
                print("Sleep Batch")
            sleep(self.sleep_batch)

        return result

    def batch(self, data, **kwargs):
        """ Override to implement what a batch does """
        raise NotImplementedError()

    def chunk(self, iterable, n, *, incomplete='fill', fillvalue=None):
        """Collect data into non-overlapping fixed-length chunks or blocks
        from https://docs.python.org/3/library/itertools.html
         grouper('ABCDEFG', 3, fillvalue='x') --> ABC DEF Gxx
         grouper('ABCDEFG', 3, incomplete='strict') --> ABC DEF ValueError
         grouper('ABCDEFG', 3, incomplete='ignore') --> ABC DEF
        """
        args = [iter(iterable)] * n
        if incomplete == 'fill':
            return itertools.zip_longest(*args, fillvalue=fillvalue)
        if incomplete == 'strict':
            return zip(*args, strict=True)
        if incomplete == 'ignore':
            return zip(*args)
        else:
            raise ValueError('Expected fill, strict, or ignore')

    def _reset_batch_count(self):
        self.batch_count = 0

class ActionsMixin:

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
                value = sep.join([task.values[x] for x in str])

        fpath.write_text(value)

    def move_to(self, fpath:pl.Path, *args, fn=None):
        """
        Move *args to fpath, with fn as the naming strategy
        only overwrite if is_backup is true
        if fpath is a file, only one arg is allowed
        """
        # Set the naming strategy:
        assert(fpath.exists() and fpath.is_dir())
        overwrite = True
        match fn:
            case FunctionType() | MethodType():
                pass
            case "overwrite":
                fn = lambda d, x: d / x.name
            case "backup":
                fn = lambda d, x: d / f"{x.parent.name}_{x.name}_backup"
            case "file":
                fn = lambda d, x: d
            case _:
                overwrite = False
                fn = lambda d, x: d / x.name

        # Then do the move
        for x in args:
            targ_path = fn(fpath, x)
            assert(overwrite or not targ_path.exists())
            logging.debug("Renaming: %s -> %s", x, targ_path)
            x.rename(targ_path)

    def copy_to(self, fpath ,*args, fn=None):
        assert(fpath.exists() and fpath.is_dir())
        overwrite = True
        match fn:
            case FunctionType() | MethodType():
                pass
            case "overwrite":
                fn = lambda d, x: d / x.name
            case "backup":
                fn = lambda d, x: d / f"{x.parent.name}_{x.name}_backup"
            case "file":
                fn = lambda d, x: d
            case _:
                overwrite = False
                fn = lambda d, x: d / x.name

        for x in args:
            target_name = fn(fpath, x)
            assert(overwrite or not (fpath / x.name).exists()), fpath / x.name
            match x.is_file():
                case True:
                    shutil.copy(x, target_name)
                case False:
                    shutil.copytree(x, target_name, dirs_exist_ok=True)

    def cmd(self, cmd:list|callable, *args, shell=False, save=None, **kwargs):
        logging.debug("Cmd: %s Args: %s kwargs: %s", cmd, args, kwargs)
        match cmd:
            case FunctionType() | MethodType():
                action = (cmd, list(args), kwargs)
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

    def get_uuids(self, *args):
        raise NotImplementedError()

    def edit_by_line(self, files:list[pl.Path], fn, inplace=True):
        for line in fileinput(files=files, inplace=inplace):
            fn(line)

    def say(self, *text):
        cmd = ["say", "-v", "Moira", "-r", "50"]
        cmd += text
        return CmdAction(cmd, shell=False)

class ZipperMixin:
    zip_name      = "default"
    zip_overwrite = False
    zip_root      = None

    def zip_create(self, fpath):
        assert(fpath.suffix== ".zip")
        if self.zip_overwrite and fpath.exists():
            fpath.unlink()
        elif fpath.exists():
            return

        logging.info("Creating Zip File: %s", fpath)
        now = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
        record_str = f"Zip File created at {now} for doot task: {self.base}"

        with zipfile.ZipFile(fpath, 'w') as targ:
            targ.writestr(".taskrecord", record_str)

    def zip_add_paths(self, fpath, *args):
        """
        Add specific files to the zip
        """
        logging.info("Adding to Zipfile: %s : %s", fpath, args)
        assert(fpath.suffix == ".zip")
        root = self.zip_root or pl.Path()
        paths = [pl.Path(x) for x in args]
        with zipfile.ZipFile(fpath, 'a') as targ:
            for file_to_add in paths:
                try:
                    relpath = file_to_add.relative_to(root)
                    attempts = 0
                    write_as = relpath
                    while str(write_as) in targ.namelist():
                        if attempts > 10:
                            print(f"Couldn't settle on a de-duplicated name for: {file_to_add}")
                            break
                        print(f"Attempted Name Duplication: {relpath}", file=sys.stderr)
                        write_as = relpath.with_stem(f"{relpath.stem}_{hex(randint(1,100))}")
                        attempts += 1

                    targ.write(str(file_to_add), write_as)

                except ValueError:
                    relpath = root / pl.Path(file_to_add).name
                except FileNotFoundError as err:
                    print(f"Adding File to Zip {fpath} failed: {err}", file=sys.stderr)

    def zip_globs(self, fpath, *globs):
        """
        Add files chosen by globs to the zip, relative to the cwd
        """
        logging.debug(f"Zip Globbing: %s : %s", fpath, globs)
        assert(fpath.suffix == ".zip")
        cwd  = pl.Path()
        root = self.zip_root or cwd
        with zipfile.ZipFile(fpath, 'a') as targ:
            for glob in globs:
                result = list(cwd.glob(glob))
                print(f"Globbed: {cwd}[{glob}] : {len(result)}")
                for dep in result:
                    try:
                        if dep.stem[0] == ".":
                            continue
                        relpath = pl.Path(dep).relative_to(root)
                        targ.write(str(dep), relpath)
                    except ValueError:
                        relpath = root / pl.Path(dep).name
                    except FileNotFoundError as err:
                        print(f"Adding File to Zip {fpath} failed: {err}", file=sys.stderr)
