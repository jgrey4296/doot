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
from doot.enums import ActionResponse_e
from doot.mixins.path_manip import PathManip_m
from doot.structs import DKey, DKeyed
from doot.actions.postbox import _DootPostBox
from doot.utils.action_decorators import IOWriter

# TODO using doot.config.settings.general.protect to disallow write/delete/backup/copy

class AppendAction(PathManip_m):
    """
      Pre/Ap-pend data from the state to a file
    """
    sep = "\n--------------------\n"

    @DKeyed.args
    @DKeyed.types("sep", fallback=None)
    @DKeyed.paths("to")
    def __call__(self, spec, state, args, sep, to):
        sep          = sep or AppendAction.sep
        loc          = to
        args_keys    = [DKey(x) for x in args]
        exp_args     = [k.expand(spec, state, fallback=None) for k in args_keys]

        if self._is_write_protected(loc):
            raise doot.errors.DootLocationError("Tried to write a protected location", loc)

        with open(loc, 'a') as f:
            for arg in exp_args:
                if not arg:
                    continue

                printer.info("Appending %s chars to %s", len(arg), loc)
                f.write(sep)
                f.write(arg)

@IOWriter()
class WriteAction(PathManip_m):
    """
      Writes data from the state to a file, accessed through the
      doot.locs object
    """

    @DKeyed.types("from", max_exp=1)
    @DKeyed.paths("to")
    def __call__(self, spec, state, _from, to) -> dict|bool|None:
        data = _from
        loc  = to

        if self._is_write_protected(loc):
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
            case _:
                as_str = str(data)
                printer.info("Writing %s chars to %s", len(as_str), loc)
                loc.write_text(as_str)

class ReadAction(PathManip_m):
    """
      Reads data from the doot.locs location to  return for the state
      The arguments of the action are held in self.spec
    """

    @DKeyed.paths("from")
    @DKeyed.redirects("update_")
    @DKeyed.types("as_bytes", fallback=False)
    @DKeyed.types("type", check=str, fallback="read")
    def __call__(self, spec, state, _from, _update, as_bytes, _type) -> dict|bool|None:
        loc = _from
        read_binary = as_bytes
        read_lines  = _type
        printer.info("Reading from %s into %s", loc, _update)
        if read_binary:
            with open(loc, "rb") as f:
                return { _update : f.read() }

        with open(loc, "r") as f:
            match read_lines:
                case "read":
                    return { _update : f.read() }
                case "lines":
                    return { _update : f.readlines() }
                case unk:
                    raise TypeError("Unknown read type", unk)

class CopyAction(PathManip_m):
    """
      copy a file somewhere
      The arguments of the action are held in self.spec

      'from' can be a string, path or list, always coerced to paths
      Can handle filename/ext globs
    """

    @DKeyed.types("from", check=str|pl.Path|list)
    @DKeyed.paths("to")
    def __call__(self, spec, state, _from, to) -> dict|bool|None:
        dest_loc   = to

        if self._is_write_protected(dest_loc):
            raise doot.errors.DootLocationError("Tried to write a protected location", to)

        match _from:
            case str() | pl.Path():
                expanded = [DKey(_from, fallback=_from, mark=DKey.mark.PATH).expand(spec, state)]
            case list():
                expanded = list(map(lambda x: DKey(x, fallback=x, mark=DKey.mark.PATH).expand(spec, state), _from))
            case _:
                raise doot.errors.DootActionError("Unrecognized type for copy sources", _from)

        if len(expanded) > 1 and not dest_loc.is_dir():
                raise doot.errors.DootActionError("Tried to copy multiple files to a non-directory")

        for arg in expanded:
            match arg:
                case pl.Path() if "*" in arg.name:
                    if not dest_loc.is_dir():
                        raise doot.errors.DootActionError("Tried to copy multiple files to a non-directory")
                    for arg_sub in arg.parent.glob(arg.name):
                        self._validate_source(arg_sub)
                        shutil.copy2(arg_sub, dest_loc)
                case pl.Path():
                    self._validate_source(arg)
                    shutil.copy2(arg, dest_loc)

    def _validate_source(self, source:pl.Path):
        match source:
            case pl.Path() if not source.exists():
                raise doot.errors.DootActionError("Tried to copy a file that doesn't exist", source)
            case pl.Path():
                return
            case _:
                raise doot.errors.DootActionError("CopyAction expected a path", source)

class MoveAction(PathManip_m):
    """
      move a file somewhere
      The arguments of the action are held in self.spec
    """

    @DKeyed.paths("from", "to")
    def __call__(self, spec, state, _from, to) -> dict|bool|None:
        source     = _from
        dest_loc   = to

        if self._is_write_protected(dest_loc):
            raise doot.errors.DootLocationError("Tried to write a protected location", dest_loc)
        if not source.exists():
            raise doot.errors.DootActionError("Tried to move a file that doesn't exist", source)
        if dest_loc.exists():
            raise doot.errors.DootActionError("Tried to move a file that already exists at the destination", dest_loc)
        if source.is_dir():
            raise doot.errors.DootActionError("Tried to move multiple files to a non-directory", source)

        source.rename(dest_loc)

class DeleteAction(PathManip_m):
    """
      delete a file / directory specified in spec.args
    """

    @DKeyed.types("recursive", "lax", check=bool, fallback=False)
    def __call__(self, spec, state, recursive, lax):
        rec = recursive
        for arg in spec.args:
            loc = DKey(arg, mark=DKey.mark.PATH).expand(spec, state)
            if self._is_write_protected(loc):
                raise doot.errors.DootLocationError("Tried to write a protected location", loc)

            if not loc.exists():
                printer.info("Not Deleting Due to non-existence: %s", loc)
                continue

            if loc.is_dir() and rec:
                printer.info("Deleting Directory: %s", loc)
                shutil.rmtree(loc)
            else:
                printer.info("Deleting File: %s", loc)
                loc.unlink(missing_ok=lax)

class BackupAction(PathManip_m):
    """
      copy a file somewhere, but only if it doesn't exist at the dest, or is newer than the dest
      The arguments of the action are held in self.spec
    """

    @DKeyed.paths("from", "to")
    @DKeyed.types("tolerance", check=int, fallback=10_000_000)
    @DKeyed.taskname
    def __call__(self, spec, state, _from, to, tolerance, _name) -> dict|bool|None:
        source_loc = _from
        dest_loc   = to

        if self._is_write_protected(dest_loc):
            raise doot.errors.DootLocationError("Tried to write a protected location", dest_loc)

        # ExFat FS has lower resolution timestamps
        # So guard by having a tolerance:
        source_ns       = source.stat().st_mtime_ns
        match dest.exists():
            case True:
                dest_ns  = dest.stat().st_mtime_ns
            case False:
                dest_ns = 1
        source_newer    = source_ns > dest_ns
        difference      = int(max(source_ns, dest_ns) - min(source_ns, dest_ns))
        below_tolerance = difference <= tolerance

        if dest_loc.exists() and ((not source_newer) or below_tolerance):
            return

        printer.warning("Backing up : %s", source_loc)
        printer.warning("Destination: %s", dest_loc)
        _DootPostBox.put(_name, dest_loc)
        shutil.copy2(source_loc,dest_loc)

class EnsureDirectory(PathManip_m):
    """
      ensure the directories passed as arguments exist
      if they don't, build them
    """

    @DKeyed.args
    def __call__(self, spec, state, args):
        for arg in args:
            loc = DKey(arg, mark=DKey.mark.PATH).expand(spec, state)
            if not loc.exists():
                printer.info("Building Directory: %s", loc)
            loc.mkdir(parents=True, exist_ok=True)

class UserInput(PathManip_m):

    @DKeyed.types("prompt", check=str, fallback="?::- ")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, prompt, _update):
        result = input(prompt)
        return { _update : result }

class SimpleFind(PathManip_m):
    """
    A Simple glob on a path
    """

    @DKeyed.paths("from")
    @DKeyed.types("rec", fallback=False)
    @DKeyed.expands("pattern")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, rec, pattern, _update):
        from_loc = _from
        match rec:
            case True:
                return { _update : list(from_loc.rglob(pattern)) }
            case False:
                return { _update : list(from_loc.glob(pattern)) }

class TouchFileAction(PathManip_m):

    @DKeyed.args
    def __call__(self, spec, state, args):
        for target in [DKey(x, mark=DKey.mark.PATH) for x in args]:
            target(spec, state).touch()

class LinkAction(PathManip_m):
    """
      for x,y in spec.args:
      x.expand().symlink_to(y.expand())
    """

    @DKeyed.paths("link", "to", fallback=None)
    @DKeyed.args
    @DKeyed.types("force", check=bool, fallback=False)
    def __call__(self, spec, state, link, to, args, force):
        if link is not None and to is not None:
            self._do_link(spec, state, spec.kwargs.link, spec.kwargs.to, force)

        for arg in spec.args:
            match arg:
                case [x,y]:
                    self._do_link(spec, state, x,y, force)
                case {"link":x, "to":list() as ys}:
                    raise NotImplementedError()
                case {"link":x, "to":y}:
                    self._do_link(spec, state, x,y, force)
                case {"from":x, "to_rel":y}:
                    raise NotImplementedError()
                case _:
                    raise TypeError("unrecognized link targets")

    def _do_link(self, spec, state, x, y, force):
        x_key  = DKey(x, mark=DKey.mark.PATH)
        y_key  = DKey(y, mark=DKey.mark.PATH)
        x_path = x_key.expand(spec, state, symlinks=True)
        y_path = y_key.expand(spec, state)
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

class ListFiles(PathManip_m):
    """ add a list of all files in a path (recursively) to the state """

    @DKeyed.paths("from")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        target = _from
        base   = target.parent
        target = target.name
        result = sh.fdfind("--color", "never", "-t", "f", "--base-directory",  str(base), ".", target, _return_cmd=True)
        filelist = result.stdout.decode().split("\n")

        printer.info("%s files in %s", len(filelist), target)
        return { _update : filelist }
