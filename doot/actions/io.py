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
import tomler
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p
from doot.utils.string_expand import expand_str
from doot.actions.postbox import DootPostBox

# TODO using doot.config.settings.general.protect to disallow write/delete/backup/copy

@doot.check_protocol
class AppendAction(Action_p):
    """
      Append data from the task_state to a file
    """
    sep = "\n--------------------\n"
    _toml_kwargs = ["sep", "target"]
    def __call__(self, spec, state):
        sep = spec.kwargs.on_fail(AppendAction.sep, str).sep()
        loc = expand_str(spec.kwargs.target, spec, state, as_path=True)
        args = [expand_str(x, spec, state) for x in spec.args]
        with open(loc, 'a') as f:
            for arg in args:
                f.write(sep)
                f.write(value)

@doot.check_protocol
class WriteAction(Action_p):
    """
      Writes data from the task_state to a file, accessed throug the
      doot.locs object
    The arguments of the action are held in self.spec
    """
    _toml_kwargs = ["fname", "target", "data" ]

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        fname = spec.kwargs.on_fail((None,)).fname()
        if fname is not None:
            fname = expand_str(fname, spec, task_state)

        data      = expand_str(spec.kwargs.data, spec, task_state)
        loc       = expand_str(spec.kwargs.target, spec, task_state, as_path=True)
        if fname is not None:
            loc = loc / fname
        printer.info("Writing to %s", loc)
        with open(loc, 'w') as f:
            f.write(data)


@doot.check_protocol
class ReadAction(Action_p):
    """
      Reads data from the doot.locs location to  return for the task_state
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = ["target", "data", "type"]

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        target_key = spec.kwargs.target
        data_key   = spec.kwargs.data
        if target_key in task_state:
            target = task_state.get(target_key)
        else:
            target = target_key

        loc = expand_str(target, spec, task_state)
        printer.info("Reading from %s into %s", loc, data_key)
        with open(loc, 'r') as f:
            match spec.kwargs.on_fail("read").type():
                case "read":
                    return { data_key : f.read() }
                case "lines":
                    return { data_key : f.readlines() }
                case unk:
                    raise TypeError("Unknown read type", unk)


@doot.check_protocol
class CopyAction(Action_p):
    """
      copy a file somewhere
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = ["source", "dest"]

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        source_key = spec.kwargs.source
        dest_key   = spec.kwargs.dest

        if source_key in task_state:
            source = task_state.get(source_key)
        else:
            source = source_key

        if dest_key in task_state:
            dest = task_state.get(dest_key)
        else:
            dest   = dest_key


        source_loc = expand_str(source, spec, task_state)
        dest_loc   = expand_str(dest, spec, task_state)
        printer.info("Copying from %s to %s", source_loc, dest_loc)
        shutil.copy2(source_loc,dest_loc)


@doot.check_protocol
class DeleteAction(Action_p):
    """
      delete a file / directory specified in spec.args
    """
    _toml_kwargs = ["recursive"]
    def __call__(self, spec, task):
        raise NotImplementedError("TODO")


@doot.check_protocol
class BackupAction(Action_p):
    """
      copy a file somewhere, but only if it doesn't exist at the dest, or is newer than the dest
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = ["source", "dest"]

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        source_key = spec.kwargs.source
        dest_key   = spec.kwargs.dest

        if source_key in task_state:
            source = task_state.get(source_key)
        else:
            source = source_key

        if dest_key in task_state:
            dest = task_state.get(dest_key)
        else:
            dest   = dest_key


        source_loc = expand_str(source, spec, task_state, as_path=True)
        dest_loc   = expand_str(dest, spec, task_state, as_path=True)

        if dest_loc.exists() and source_loc.stat().st_mtime_ns <= dest_loc.stat().st_mtime_ns:
            return True

        printer.warning("Backing up %s to %s", source_loc, dest_loc)
        DootPostBox.put_from(task_state, dest_loc)
        shutil.copy2(source_loc,dest_loc)


@doot.check_protocol
class EnsureDirectory(Action_p):
    """
      ensure the directories passed as arguments exist
      if they don't, build them
    """

    def __call__(self, spec, task_state:dict):
        printer.debug("Ensuring Directories: %s", spec.args)
        for arg in spec.args:
            loc = expand_str(arg, spec, task_state, as_path=True)
            loc.mkdir(parents=True, exist_ok=True)


@doot.check_protocol
class ReadJson(Action_p):
    """
      Read a json file `and add it to the task state as task_state[`data`] = Tomler(json_data)
    """
    _toml_kwargs = ["target", "data"]

    def __call__(self, spec, task_state:dict):
        fpath = expand_str(spec.kwargs.target, spec, task_state, as_path=True)
        data = json.load(fpath)
        return {spec.kwargs.data : tomler.Tomler(data)}


@doot.check_protocol
class UserInput(Action_p):

    _toml_kwargs = ["target", "prompt"]

    def __call__(self, spec, state):
        prompt = spec.kwargs.on_fail("?::- ").prompt()
        target = spec.kwargs.target
        result = input(prompt)
        return { target : result }
