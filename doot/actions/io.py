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
from doot.utils.string_expand import expand_str, expand_set, expand_key
from doot.actions.postbox import _DootPostBox

# TODO using doot.config.settings.general.protect to disallow write/delete/backup/copy

@doot.check_protocol
class AppendAction(Action_p):
    """
      Append data _from the task_state to a file
    """
    sep = "\n--------------------\n"
    _toml_kwargs = ["sep", "to"]

    def __call__(self, spec, state):
        sep     = spec.kwargs.on_fail(AppendAction.sep, str).sep()
        loc     = expand_key(spec.kwargs.on_fail("to").to_(), spec, state, as_path=True)
        args    = [expand_str(x, spec, state) for x in spec.args]
        with open(loc, 'a') as f:
            for arg in args:
                value = expand_str(arg, spec, state)
                printer.info("Appending %s chars to %s", len(value), loc)
                f.write(sep)
                f.write(value)

@doot.check_protocol
class WriteAction(Action_p):
    """
      Writes data _from the task_state to a file, accessed throug the
      doot.locs object
    The arguments of the action are held in self.spec

      { do="write!" _from="{data}" to="{temp}/{fname}" }
    """
    _toml_kwargs = ["from_", "to" ]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        data              = expand_key(spec.kwargs.on_fail("from_").from_(), spec, task_state)
        loc_key           = expand_key(spec.kwargs.on_fail("to").to_(), spec, task_state)
        loc               = expand_str(loc_key, spec, task_state, as_path=True)
        printer.info("Writing %s chars to %s", len(data), loc)
        with open(loc, 'w') as f:
            f.write(data)


@doot.check_protocol
class ReadAction(Action_p):
    """
      Reads data _from the doot.locs location to  return for the task_state
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = ["_from", "update_", "type", "as_bytes"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        data_key   = expand_str(spec.kwargs.update_, spec, task_state)
        loc        = expand_key(spec.kwargs.on_fail("_from").from_(), spec, task_state, as_path=True)
        read_type  = "rb" if spec.kwargs.on_fail(False).as_bytes() else "r"

        printer.info("Reading _from %s into %s", loc, data_key)
        match read_type:
            case "r":
                with open(loc, "r") as f:
                    match spec.kwargs.on_fail("read").type():
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
    _toml_kwargs = ["_from", "to"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        sources = []
        dest_loc   = expand_key(spec.kwargs.on_fail("to").to_(), spec, task_state, as_path=True)
        if bool(spec.args) and not spec.kwargs.on_fail(False)._from():
            printer.info("Copying into directory %s: %s", spec.args, dest_loc)
            expanded = expand_set(spec.args, spec, task_state, as_path=True)
            if any(not x.exists() for x in expanded):
                raise doot.errors.DootActionError("Tried to copy a file that doesn't exist")
            if any((dest_loc/x.name).exists() for x in expanded):
                raise doot.errors.DootActionError("Tried to copy a file that already exists at the destination")
            if len(expanded) > 1 and not dest_loc.is_dir():
                raise doot.errors.DootActionError("Tried to copy multiple files to a non-directory")

            for arg in expanded:
                shutil.copy2(arg, dest_loc)

        elif spec.kwargs.on_fail(False)._from():
            expanded = expand_set(spec.kwargs._from, spec, task_state, as_path=True)
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
    _toml_kwargs = ["recursive", "lax"]
    def __call__(self, spec, task):
        for arg in spec.args:
            loc = expand_str(arg, spec, task, as_path=True)
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
    _toml_kwargs = ["_from", "to"]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        source_loc = expand_key(spec.kwargs.on_fail("_from").from_(), spec, task_state, as_path=True)
        dest_loc   = expand_key(spec.kwargs.on_fail("to").to_(), spec, task_state, as_path=True)

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
            loc = expand_str(arg, spec, task_state, as_path=True)
            printer.debug("Building Directory: %s", loc)
            loc.mkdir(parents=True, exist_ok=True)


@doot.check_protocol
class ReadJson(Action_p):
    """
        Read a json file `and add it to the task state as task_state[`data`] = TomlGuard(json_data)
    """
    _toml_kwargs = ["_from", "update_"]

    def __call__(self, spec, task_state:dict):
        data_key = expand_str(spec.kwargs.update_, spec, task_state)
        fpath    = expand_key(spec.kwargs.on_fail("_from").from_(), spec, task_state, as_path=True)
        data     = json.load(fpath)
        return { data_key : TG.TomlGuard(data) }


@doot.check_protocol
class UserInput(Action_p):

    _toml_kwargs = ["update_", "prompt"]

    def __call__(self, spec, state):
        prompt = expand_str(spec.kwargs.on_fail("?::- ").prompt(), spec, state)
        target = expand_str(spec.kwargs.update_, spec, state)
        result = input(prompt)
        return { target : result }


@doot.check_protocol
class SimpleFind(Action_p):
    """

    """

    _toml_kwargs = ["_from", "pattern_", "rec", "update_"]

    def __call__(self, spec, task):
        from_loc     = expand_key(spec.kwargs.on_fail("_from").from_(), spec, task, as_path=True)
        pattern      = expand_key(spec.kwargs.on_fail("pattern").pattern_(), spec, task)
        data_key     = expand_str(spec.kwargs.update_, spec, task)
        match spec.kwargs.on_fail(False).rec():
            case True:
                return { data_key : list(from_loc.rglob(pattern)) }
            case False:
                return { data_key : list(from_loc.glob(pattern)) }
