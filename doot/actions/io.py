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
# import json
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
from doot.enums import ActionResponseEnum
from doot._abstract import Action_p
from doot.structs import DootKey
from doot.actions.postbox import _DootPostBox

# TODO using doot.config.settings.general.protect to disallow write/delete/backup/copy

##-- expansion keys
TO_KEY             : Final[DootKey] = DootKey.make("to")
FROM_KEY           : Final[DootKey] = DootKey.make("from")
UPDATE             : Final[DootKey] = DootKey.make("update_")
PROMPT             : Final[DootKey] = DootKey.make("prompt")
PATTERN            : Final[DootKey] = DootKey.make("pattern")
SEP                : Final[DootKey] = DootKey.make("sep")
TYPE_KEY           : Final[DootKey] = DootKey.make("type")
AS_BYTES           : Final[DootKey] = DootKey.make("as_bytes")
FILE_TARGET        : Final[DootKey] = DootKey.make("file")
RECURSIVE          : Final[DootKey] = DootKey.make("recursive")
LAX                : Final[DootKey] = DootKey.make("lax")
##-- end expansion keys


@doot.check_protocol
class AppendAction(Action_p):
    """
      Append data from the task_state to a file
    """
    sep = "\n--------------------\n"
    _toml_kwargs = [SEP, TO_KEY, "args"]

    def __call__(self, spec, state):
        sep     = SEP.to_type(spec, state, type_=str|None) or AppendAction.sep
        loc     = TO_KEY.to_path(spec, state)
        args    = [DootKey.make(x, explicit=True).expand(spec, state, insist=True, on_fail=None) for x in spec.args]

        if not doot.locs.check_writable(loc):
            raise doot.errors.DootLocationError("Tried to write a protected location", loc)

        with open(loc, 'a') as f:
            for arg in args:
                if not arg:
                    continue

                printer.info("Appending %s chars to %s", len(arg), loc)
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
        data = FROM_KEY.to_type(spec, task_state, on_fail=None)
        loc  = TO_KEY.to_path(spec, task_state)

        if not doot.locs.check_writable(loc):
            raise doot.errors.DootLocationError("Tried to write a protected location", loc)

        match data:
            case None:
                printer.info("No Data to Write")
            case _ if not bool(data):
                printer.info("No Data to Write")
            case [*xs]:
                text = "\n".join(xs)
                printer.info("Writing %s chars to %s", len(text), loc)
                loc.write_text(text)
            case bytes():
                printer.info("Writing %s bytes to %s", len(data), loc)
                loc.write_bytes(data)
            case str():
                printer.info("Writing %s chars to %s", len(data), loc)
                loc.write_text(data)



@doot.check_protocol
class ReadAction(Action_p):
    """
      Reads data from the doot.locs location to  return for the task_state
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [FROM_KEY, UPDATE, TYPE_KEY, AS_BYTES],

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        data_key    = UPDATE.redirect(spec)
        loc         = FROM_KEY.to_path(spec, task_state)
        read_binary = AS_BYTES.to_type(spec, task_state, on_fail=False)
        read_lines  = TYPE_KEY.to_type(spec, task_state, type_=str, on_fail="read")

        printer.info("Reading from %s into %s", loc, data_key)
        if read_binary:
            with open(loc, "rb") as f:
                return { data_key : f.read() }

        with open(loc, "r") as f:
            match read_lines:
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
    _toml_kwargs = [FROM_KEY, TO_KEY]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        dest_loc   = TO_KEY.to_path(spec, task_state)
        sources    = FROM_KEY.to_type(spec, task_state, type_=list|str|pl.Path)
        match sources:
            case str() | pl.Path():
                expanded = [DootKey.make(sources, strict=False).to_path(spec, task_state)]
            case list():
                expanded = list(map(lambda x: DootKey.make(x, strict=False).to_path(spec, task_state), sources))
            case _:
                raise doot.errors.DootActionError("Unrecognized type for copy sources", sources)


        if not all(doot.locs.check_writable(x) for x in expanded):
            raise doot.errors.DootLocationError("Tried to write a protected location", expanded)
        if any(not x.exists() for x in expanded):
            raise doot.errors.DootActionError("Tried to copy a file that doesn't exist")
        if any((dest_loc/x.name).exists() for x in expanded):
            raise doot.errors.DootActionError("Tried to copy a file that already exists at the destination")
        if len(expanded) > 1 and not dest_loc.is_dir():
            raise doot.errors.DootActionError("Tried to copy multiple files to a non-directory")

        for arg in expanded:
            shutil.copy2(arg, dest_loc)

@doot.check_protocol
class MoveAction(Action_p):
    """
      move a file somewhere
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [FROM_KEY, TO_KEY]

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        dest_loc   = TO_KEY.to_path(spec, task_state)
        source     = FROM_KEY.to_path(spec, task_state)

        if not doot.locs.check_writable(dest_loc):
            raise doot.errors.DootLocationError("Tried to write a protected location", dest_loc)
        if not source.exists():
            raise doot.errors.DootActionError("Tried to move a file that doesn't exist", source)
        if dest_loc.exists():
            raise doot.errors.DootActionError("Tried to move a file that already exists at the destination", dest_loc)
        if source.is_dir():
            raise doot.errors.DootActionError("Tried to move multiple files to a non-directory", source)

        source.rename(dest_loc)

@doot.check_protocol
class DeleteAction(Action_p):
    """
      delete a file / directory specified in spec.args
    """
    _toml_kwargs = [RECURSIVE, "lax", "args"]

    def __call__(self, spec, state):
        rec = RECURSIVE.to_type(spec, state, type_=bool, on_fail=False)
        lax = LAX.to_type(spec, state, type_=bool, on_fail=False)
        for arg in spec.args:
            loc = DootKey.make(arg, explicit=True).to_path(spec, state)
            if not doot.locs.check_writable(loc):
                raise doot.errors.DootLocationError("Tried to delete a protected location", loc)

            printer.info("Deleting %s", loc)
            if loc.is_dir() and rec:
                shutil.rmtree(loc)
            else:
                loc.unlink(missing_ok=lax)


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

        if not doot.locs.check_writable(dest_loc):
            raise doot.errors.DootLocationError("Tried to write a protected location", dest_loc)

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
            loc = DootKey.make(arg, explicit=True).to_path(spec, task_state)
            if not loc.exists():
                printer.info("Building Directory: %s", loc)
            loc.mkdir(parents=True, exist_ok=True)


@doot.check_protocol
class UserInput(Action_p):

    _toml_kwargs = [UPDATE, PROMPT]

    def __call__(self, spec, state):
        prompt = PROMPT.to_type(spec, state, type_=str, on_fail="?::- ")
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
        pattern  = PATTERN.expand(spec, state)
        data_key = UPDATE.redirect(spec)
        match spec.kwargs.on_fail(False).rec():
            case True:
                return { data_key : list(from_loc.rglob(pattern)) }
            case False:
                return { data_key : list(from_loc.glob(pattern)) }


@doot.check_protocol
class TouchFileAction(Action_p):

    def __call__(self, spec, state):
        target = FILE_TARGET.to_path(spec, state)
        target.touch()


@doot.check_protocol
class LinkAction(Action_p):
    """
      for x,y in spec.args:
      x.to_path().symlink_to(y.to_path())
    """
    FORCE = DootKey.make("force")
    LINK = DootKey.make("link")
    TO = DootKey.make("to")

    def __call__(self, spec, state):
        if self.LINK in spec.kwargs and self.TO in spec.kwargs:
            self._do_link(spec.kwargs.link, spec.kwargs.to, spec, state)

        for arg in spec.args:
            match arg:
                case [x,y]:
                    self._do_link(x,y, spec, state)
                case {"link":x, "to":list() as ys}:
                    raise NotImplementedError()
                case {"link":x, "to":y}:
                    self._do_link(x,y, spec, state)
                case {"from":x, "to_rel":y}:
                    raise NotImplementedError()
                case _:
                    raise TypeError("unrecognized link targets")

    def _do_link(self, x, y, spec, state):
        x_key  = DootKey.make(x, explicit=True)
        y_key  = DootKey.make(y, explicit=True)
        x_path = x_key.to_path(spec, state, symlinks=True)
        y_path = y_key.to_path(spec, state)
        force  = bool(self.FORCE.to_type(spec, state, on_fail=False))
        # TODO when py3.12: use follow_symlinks=False
        if (x_path.exists() or x_path.is_symlink()) and not force:
            printer.warning("SKIP: A Symlink already exists: %s -> %s", x_path, x_path.resolve())
            return
        if not y_path.exists():
            raise doot.errors.DootActionError("Symlink target does not exist", y_path)
        if force and x_path.is_symlink():
            printer.warning("Forcing New Symlink")
            x_path.unlink()
        printer.info("Linking: %s -> %s", x_path, y_path)
        x_path.symlink_to(y_path)


@doot.check_protocol
class ListFiles(Action_p):
    """ add a list of all files in a path (recursively) to the state """

    def __call__(self, spec, state):
        update = UPDATE.redirect(spec)
        target = FROM_KEY.to_path(spec, state)
        base   = target.parent
        target = target.name
        result = sh.fdfind("--color", "never", "-t", "f", "--base-directory",  str(base), ".", target, _return_cmd=True)
        filelist = result.stdout.decode().split("\n")

        printer.info("%s files in %s", len(filelist), target)
        return { update : filelist }
