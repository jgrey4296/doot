#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

from tomlguard import TomlGuard
import doot
import doot.constants
from doot.errors import DootDirAbsent
from doot.mixins.job.subtask import SubTask_M
from doot.structs import DootTaskSpec, DootActionSpec, DootKey, DootCodeReference
from doot.actions.postbox import _DootPostBox

walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()

class _WalkControl(enum.Enum):
    """
    accept  : is a result, and descend if recursive
    keep    : is a result, don't descend
    discard : not a result, descend
    reject  : not a result, don't descend
    """
    yesAnd  = enum.auto()
    yes     = enum.auto()
    noBut   = enum.auto()
    no      = enum.auto()

def id_retriever(spec, state) -> list[dict]:
    return []

class Expander_M(SubTask_M):
    """
      A Job Mixin that creates a subtask for each entry in a list,
      useful for postbox expansion and cli arg expansion
    """
    _default_subtask_injections = []

    def __init__(self, spec):
        super().__init__(spec)
        match spec.extra.on_fail(None, None|str).retriever():
            case str() as x:
                retriever_ref = DootCodeReference.from_str(x)
                self._retriever_fn = retriever_ref.try_import()
            case None:
                self._retriever_fn = id_retriever
            case _ as f if callable(f):
                self._retriever_fn = f

    def _build_subs(self) -> Generator[DootTaskSpec]:
        base               = self.fullname
        for i, data in enumerate(self._retriever_fn(self.spec, self.state)):
            match data:
                case {"name": x}:
                    uname = base.subtask(i, x)
                case _:
                    uname = base.subtask(i)
            inject_keys = set(self.spec.inject).difference(self._default_subtask_injections)
            inject_dict = {k: self.spec.extra[k] for k in inject_keys}

            match self._build_subtask(i, uname, **data, **inject_dict):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))

    @classmethod
    def stub_class(cls, stub):
        stub['retriever'].set(type="CodeReference",

                              default="doot.mixins.job.list_expander:id_retriever",
                              priority=80,
                              comment="fn(spec, state) -> list[dict]")

class PostBoxExpander_M(Expander_M):
    """
      A Job mixin to create subtasks for each entry in a retrieved postbox list
    """

    def __init__(self, spec):
        super().__init__(spec)
        self.task_key     = spec.extra.postbox.task
        self.sub_key      = spec.extra.postbox.sub_key
        self.inject_key   = spec.extra.postbox.inject_key
        self.flatten_data = spec.extra.on_fail(False, bool).postbox.flatten()

    def _build_subs(self) -> Generator[DootTaskSpec]:
        base          = self.fullname
        result : list = _DootPostBox.get(self.task_key, subkey=self.sub_key)
        inject_keys   = set(self.spec.inject)
        inject_dict   = {k: self.spec.extra[k] for k in inject_keys}
        for i, data in enumerate(result):
            uname = base.subtask(i)
            if isinstance(data, dict) and self.flatten_data:
                data_inject = data
            else:
                data_inject = { self.inject_key : data }

            match self._build_subtask(i, uname, **data_inject, **inject_dict):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))

    @classmethod
    def stub_class(cls, stub):
        stub['postbox'].set(type="dict", default={"inject_key": "data", "task": "", "sub_key":"-"}, priority=80, comment="{'inject_key': 'data', 'task': '', 'sub_key':'-'} : the taskname and subbox to expand. option: flatten=bool")

class WalkExpander_M(Expander_M):
    """
    Base job for file based walking.
    Each File found is a separate subtask

    Uses the toml key `sub_task` to spec each task,
    and `head_task` for a final task to run after all subtasks finish

    Each Subtask gets keys added to its state: [fpath, fstem. fname, lpath]
    `exts` filters by extension (py-style, so eg: '.bib')
    `roots` defines starting locations.
    `recursive` controls if just the specified location is searched, or subdirs.
    `accept_fn` allows an import path of a callable: lambda(pl.Path) -> _WalkControl

    Config files can specify:
    settings.walking.ignores = []
    settings.walking.halts   = []

    Override as necessary:
    .filter : for controlling results
    .walk_target : for what is walked
    .{top/subtask/setup/teardown}_detail : for controlling task definition
    .{top/subtask/setup/teardown}_actions : for controlling task actions
    .default_task : the basic task definition that everything customises
    """
    control = _WalkControl
    _default_subtask_injections = ["fpath","fstem","fname","lpath","pstem"]

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)
        self._retriever_fn = self.walk_all
        match self.spec.extra.on_fail(None, None|str).accept_fn():
            case None:
                self._accept_fn = self.filter
            case str() as x:
                accept_ref = DootCodeReference.from_str(x)
                self._accept_fn = accept_ref.try_import()

        self.exts           = {y for x in spec.extra.on_fail([]).exts() for y in [x.lower(), x.upper()]}
        # expand roots based on doot.locs
        self.roots = []
        for root in spec.extra.on_fail([pl.Path()], list).roots():
            key = DootKey.make(root)
            self.roots.append(key.to_path(None, spec.extra))

        self.rec            = spec.extra.on_fail(False, bool).recursive()
        self.total_subtasks = 0
        for x in self.roots:
            depth = len(set(self.__class__.mro()) - set(super().__class__.mro()))
            if not x.exists():
                logging.warning(f"Walker Missing Root: {x}", stacklevel=depth)
            if not x.is_dir():
                 logging.warning(f"Walker Root is a file: {x}", stacklevel=depth)

    def filter(self, target:pl.Path) -> bool | _WalkControl:
        """ filter function called on each prospective walk result
        override in subclasses as necessary
        """
        return True

    def rel_path(self, fpath) -> pl.Path:
        """
        make the path relative to the appropriate root
        """
        for root in self.roots:
            try:
                return fpath.relative_to(root)
            except ValueError:
                continue

        raise ValueError(f"{fpath} is not able to be made relative")

    def walk_target(self, target, rec=None, fn=None, exts=None) -> Generator[pl.Path]:
        rec       = bool(rec) or rec is None and self.rec
        exts      = exts or self.exts or []
        accept_fn = fn or self._accept_fn
        printer.info("Walking Target: %s : rec=%s, exts=%s", target, rec, exts)

        if not target.exists():
            return None

        if not rec:
            yield from self._single_directory_walk(target, accept_fn, exts)
            return None

        assert(rec)
        queue = [target]
        while bool(queue):
            current = queue.pop()
            if not current.exists():
                continue
            if current.name in walk_ignores:
                continue
            if current.is_dir() and any([(current / x).exists() for x in walk_halts]):
                continue
            if bool(exts) and current.is_file() and current.suffix not in exts:
                continue
            match accept_fn(current):
                case _WalkControl.yes:
                    yield current
                case True if current.is_dir():
                    queue += sorted(current.iterdir())
                case True | _WalkControl.yesAnd:
                    yield current
                    if current.is_dir():
                        queue += sorted(current.iterdir())
                case False | _WalkControl.noBut if current.is_dir():
                    queue += sorted(current.iterdir())
                case None | False:
                    continue
                case _WalkControl.no | _WalkControl.noBut:
                    continue
                case _ as x:
                    raise TypeError("Unexpected filter value", x)

    def walk_all(self, spec, state) -> Generator[dict]:
        """
        walk all available targets,
        and generate unique names for them
        """
        base_name   = self.fullname
        found_names = set()
        for root in self.roots:
            for fpath in self.walk_target(root):
                # ensure unique task names
                parts = self.rel_path(fpath).parts
                if not bool(parts):
                    parts = [fpath.stem]
                curr = 1

                name = base_name.subtask(parts[-curr])
                logging.debug("Building Unique name for: %s : %s", name, fpath)
                while name in found_names and curr < len(parts):
                    curr += 1
                    name = base_name.subtask(*parts[-curr:])

                found_names.add(name)
                yield dict(name=name,
                           fpath=fpath,
                           fstem=fpath.stem,
                           fname=fpath.name,
                           lpath=self.rel_path(fpath),
                           pstem=fpath.parent.stem)

        logging.debug("Walked: %s", len(found_names))

    def _single_directory_walk(self, target, accept_fn, exts):
        check_fn = lambda x: (accept_fn(x) not in [None, False, _WalkControl.no, _WalkControl.noBut]
                                and x.name not in walk_ignores
                                and (not bool(exts) or (x.is_file() and x.suffix in exts)))

        if check_fn(target):
            yield target

        if not target.is_dir():
            return None

        for x in target.iterdir():
            if check_fn(x):
                yield x

    @classmethod
    def stub_class(cls, stub):
        del stub['retriever']
        stub['exts'].set(type="list[str]",          default=[],      priority=80)
        stub['roots'].set(type="list[str|pl.Path]", default=['.'],   priority=80, comment="Places the Walker will start")
        stub['recursive'].set(type="bool",          default=False,   priority=80)
        stub['accept_fn'].set(type="callable",      prefix="# ",     priority=81, comment="callable[[pl.Path], bool|_WalkControl]")

class WalkerExternal_M(WalkExpander_M):

    def walk_all(self, spec, state) -> Generator[tuple(str, pl.Path)]:
        """
          run the spec's `cmd`, expanded with `exts`, for each entry in `roots`
          combine, and return
        """
        base_name     = self.fullname
        found_names   = set()
        cmd           = sh.Command(self.spec.extra.cmd)
        baked         = cmd.bake(*self.spec.extra.cmd_args)
        for root in self.roots:
            results = baked(root)
            for fpath in results:
                # ensure unique task names
                curr = fpath.absolute()
                name = base_name.subtask(curr.stem)
                logging.debug("Building Unique name for: %s : %s", name, fpath)
                while name in found_names:
                    curr = curr.parent
                    name = name.subtask(curr.stem)

                found_names.add(name)
                yield name, fpath

    @classmethod
    def stub_class(cls, stub):
        stub['cmd'].set(type="string",         default="fdfind")
        stub['cmd_args'].set(type="list[str]", default=["--color", "never"])
