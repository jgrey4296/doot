## base_action.py -*- mode: python -*-
##-- imports
from __future__ import annotations

# import abc
import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import json
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

printer = logmod.getLogger("doot._printer")

from time import sleep
import sh
import shutil
import tomlguard as TG
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p
import doot.utils.expansion as exp
from doot.actions.postbox import _DootPostBox

# TODO using doot.config.settings.general.protect to disallow write/delete/backup/copy

##-- expansion keys
TO_KEY        : Final[exp.DootKey] = exp.DootKey("to")
FROM_KEY      : Final[exp.DootKey] = exp.DootKey("from")
UPDATE        : Final[exp.DootKey] = exp.DootKey("update_")
PROMPT        : Final[exp.DootKey] = exp.DootKey("prompt")
PATTERN       : Final[exp.DootKey] = exp.DootKey("pattern")
SEP           : Final[exp.DootKey] = exp.DootKey("pattern")
TYPE_KEY      : Final[exp.DootKey] = exp.DootKey("type")
AS_BYTES      : Final[exp.DootKey] = exp.DootKey("as_bytes")
##-- end expansion keys

@doot.check_protocol
class AppendAction(Action_p):
    """
      Append data from the task_state to a file
    """
    sep = "\n--------------------\n"
    _toml_kwargs = [SEP, TO_KEY, "args"]

    def __call__(self, spec, state):
        sep     = SEP.to_type(spec, task_state, type_=str|None) or AppendAction.sep
        loc     = TO_KEY.to_path(spec, state)
        args    = [exp.to_str(x, spec, state) for x in spec.args]
        with open(loc, 'a') as f:
            for arg in args:
                printer.info("Appending %s chars to %s", len(value), loc)
                f.write(sep)
                f.write(arg)

@doot.check_protocol
class WriteAction(Action_p):
    """
      Writes data from the task_state to a file, accessed through the
      doot.locs object
    The arguments of the action are held in self.spec

      { do="write!" from="{data}" to="{temp}/{fname}" }
    """
    _toml_kwargs = [FROM_KEY, TO_KEY]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        data = FROM_KEY.expand(spec, task_state)
        loc  = TO_KEY.to_path(spec, task_state)
        printer.info("Writing %s chars to %s", len(data), loc)
        with open(loc, 'w') as f:
            f.write(data)


@doot.check_protocol
class ReadAction(Action_p):
    """
      Reads data from the doot.locs location to  return for the task_state
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [FROM_KEY, UPDATE, TYPE_KEY, AS_BYTES],

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        data_key   = UPDATE.redirect(spec)
        loc        = FROM_KEY.to_path(spec, task_state)
        read_type  = "rb" if spec.kwargs.on_fail(False)[AS_BYTES]() else "r"

        printer.info("Reading from %s into %s", loc, data_key)
        match read_type:
            case "r":
                with open(loc, "r") as f:
                    match spec.kwargs.on_fail("read")[TYPE_KEY]():
                        case "read":
                            return { data_key : f.read() }
                        case "lines":
                            return { data_key : f.readlines() }
                        case unk:
                            raise TypeError("Unknown read type", unk)
            case "rb":
                with open(loc, "rb") as f:
                    return { data_key : f.read() }


@doot.check_protocol
class CopyAction(Action_p):
    """
      copy a file somewhere
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [FROM_KEY, TO_KEY]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        dest_loc   = TO_KEY.to_path(spec, task_state)
        sources    = FROM_KEY.to_type(spec, task_state, type_=list|str|pl.Path)
        match sources:
            case str() | pl.Path():
                expanded = [exp.to_path(sources, spec, task_state)]
            case list():
                expanded = list(map(lambda x: exp.to_path(x, spec, task_state), sources))
            case _:
                raise doot.errors.DootActionError("Unrecognized type for copy sources", sources)

        if any(not x.exists() for x in expanded):
            raise doot.errors.DootActionError("Tried to copy a file that doesn't exist")
        if any((dest_loc/x.name).exists() for x in expanded):
            raise doot.errors.DootActionError("Tried to copy a file that already exists at the destination")
        if len(expanded) > 1 and not dest_loc.is_dir():
            raise doot.errors.DootActionError("Tried to copy multiple files to a non-directory")

        for arg in expanded:
            shutil.copy2(arg, dest_loc)

@doot.check_protocol
class DeleteAction(Action_p):
    """
      delete a file / directory specified in spec.args
    """
    _toml_kwargs = ["recursive", "lax", "args"]
    def __call__(self, spec, task):
        for arg in spec.args:
            loc = exp.to_path(arg, spec, task)
            printer.info("Deleting %s", loc)
            if loc.is_dir() and spec.kwargs.on_fail(False).recursive():
                shutil.rmtree(loc)
            else:
                loc.unlink(missing_ok=spec.kwargs.on_fail(False).lax())


@doot.check_protocol
class BackupAction(Action_p):
    """
      copy a file somewhere, but only if it doesn't exist at the dest, or is newer than the dest
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [FROM_KEY, TO_KEY]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        source_loc = FROM_KEY.to_path(spec, task_state)
        dest_loc   = TO_KEY.to_path(spec, task_state)

        if dest_loc.exists() and source_loc.stat().st_mtime_ns <= dest_loc.stat().st_mtime_ns:
            return True

        printer.warning("Backing up : %s", source_loc)
        printer.warning("Destination: %s", dest_loc)
        _DootPostBox.put_from(task_state, dest_loc)
        shutil.copy2(source_loc,dest_loc)


@doot.check_protocol
class EnsureDirectory(Action_p):
    """
      ensure the directories passed as arguments exist
      if they don't, build them
    """

    def __call__(self, spec, task_state:dict):
        for arg in spec.args:
            loc = exp.to_path(arg, spec, task_state)
            printer.debug("Building Directory: %s", loc)
            loc.mkdir(parents=True, exist_ok=True)


@doot.check_protocol
class ReadJson(Action_p):
    """
        Read a json file and add it to the task state as task_state[`data`] = TomlGuard(json_data)
    """
    _toml_kwargs = [FROM_KEY, UPDATE]

    def __call__(self, spec, task_state:dict):
        data_key = UPDATE.redirect(spec)
        fpath    = FROM_KEY.to_path(spec, task_state)
        data     = json.load(fpath)
        return { data_key : TG.TomlGuard(data) }


@doot.check_protocol
class UserInput(Action_p):

    _toml_kwargs = [UPDATE, PROMPT]

    def __call__(self, spec, state):
        prompt = PROMPT.to_any(spec, state, type_=str|None) or "?::- "
        target = UPDATE.redirect(spec)
        result = input(prompt)
        return { target : result }


@doot.check_protocol
class SimpleFind(Action_p):
    """

    """

    _toml_kwargs = [FROM_KEY, PATTERN, UPDATE, "rec"]

    def __call__(self, spec, state):
        from_loc = FROM_KEY.to_path(spec, state)
        pattern  = PATTERN.to_str(spec, state)
        data_key = UPDATE.redirect(spec)
        match spec.kwargs.on_fail(False).rec():
            case True:
                return { data_key : list(from_loc.rglob(pattern)) }
            case False:
                return { data_key : list(from_loc.glob(pattern)) }
