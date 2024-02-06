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
      Append data from the state to a file
    """
    sep = "\n--------------------\n"
    _toml_kwargs = [SEP, TO_KEY, "args"]

    @DootKey.kwrap.types("sep", hint={"on_fail":None})
    @DootKey.kwrap.paths("to")
    def __call__(self, spec, state, sep, to):
        sep     = sep or AppendAction.sep
        loc     = to
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
      Writes data from the state to a file, accessed through the
      doot.locs object
    """

    @DootKey.kwrap.types("from")
    @DootKey.kwrap.paths("to")
    def __call__(self, spec, state, _from, to) -> dict|bool|None:
        data = _from
        loc  = to

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
      Reads data from the doot.locs location to  return for the state
      The arguments of the action are held in self.spec
    """
    _toml_kwargs = [TYPE_KEY, AS_BYTES],

    @DootKey.kwrap.types("from")
    @DootKey.kwrap.redirects("update_")
    @DootKey.kwrap.types("as_bytes", hint={"on_fail":False})
    @DootKey.kwrap.types("type", hint={"type_":str, "on_fail":"read"})
    def __call__(self, spec, state, _from, _update, as_bytes, _type) -> dict|bool|None:
        loc         = _from
        read_binary = as_bytes
        read_lines  = type_

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


@doot.check_protocol
class CopyAction(Action_p):
    """
      copy a file somewhere
      The arguments of the action are held in self.spec
    """

    @DootKey.kwrap.types("from", hint={"type_":str|pl.Path|list})
    @DootKey.kwrap.paths("to")
    def __call__(self, spec, state, _from, to) -> dict|bool|None:
        dest_loc   = to
        match _from:
            case str() | pl.Path():
                expanded = [DootKey.make(_from, strict=False).to_path(spec, state)]
            case list():
                expanded = list(map(lambda x: DootKey.make(x, strict=False).to_path(spec, state), _from))
            case _:
                raise doot.errors.DootActionError("Unrecognized type for copy sources", _from)


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

    @DootKey.kwrap.paths("from", "to")
    def __call__(self, spec, state, _from, to) -> dict|bool|None:
        source     = _from
        dest_loc   = to

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
    @DootKey.kwrap.types("recursive", "lax", hint={"type_":bool, "on_fail":False})
    def __call__(self, spec, state, recursive, lax):
        rec = recursive
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

    @DootKey.kwrap.paths("from", "to")
    def __call__(self, spec, state, _from, to) -> dict|bool|None:
        source_loc = _from
        dest_loc   = to

        if not doot.locs.check_writable(dest_loc):
            raise doot.errors.DootLocationError("Tried to write a protected location", dest_loc)

        if dest_loc.exists() and source_loc.stat().st_mtime_ns <= dest_loc.stat().st_mtime_ns:
            return True

        printer.warning("Backing up : %s", source_loc)
        printer.warning("Destination: %s", dest_loc)
        _DootPostBox.put_from(state, dest_loc)
        shutil.copy2(source_loc,dest_loc)


@doot.check_protocol
class EnsureDirectory(Action_p):
    """
      ensure the directories passed as arguments exist
      if they don't, build them
    """

    @DootKey.kwrap.args
    def __call__(self, spec, state, args):
        for arg in args:
            loc = DootKey.make(arg, explicit=True).to_path(spec, state)
            if not loc.exists():
                printer.info("Building Directory: %s", loc)
            loc.mkdir(parents=True, exist_ok=True)


@doot.check_protocol
class UserInput(Action_p):

    @DootKey.kwrap.types("prompt", hint={"type_":str, "on_fail":"?::- "})
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, prompt, _update):
        result = input(prompt)
        return { _update : result }


@doot.check_protocol
class SimpleFind(Action_p):
    """
    A Simple glob on a path
    """

    @DootKey.kwrap.paths("from")
    @DootKey.kwrap.types("rec", hint={"on_fail":False})
    @DootKey.kwrap.expands("pattern")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, _from, rec, pattern, _update):
        from_loc = _from
        match rec:
            case True:
                return { _update : list(from_loc.rglob(pattern)) }
            case False:
                return { _update : list(from_loc.glob(pattern)) }


@doot.check_protocol
class TouchFileAction(Action_p):

    @DootKey.kwrap.args
    def __call__(self, spec, state, args):
        for target in [DootKey.make(x, exp_as="path") for x in args]:
            target(spec, state).touch()


@doot.check_protocol
class LinkAction(Action_p):
    """
      for x,y in spec.args:
      x.to_path().symlink_to(y.to_path())
    """
    @DootKey.kwrap.paths("link", "to", hint={"on_fail":None})
    @DootKey.kwrap.args
    @DootKey.kwrap.types("force", hint={"type_":bool, "on_fail":False})
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
        x_key  = DootKey.make(x, explicit=True)
        y_key  = DootKey.make(y, explicit=True)
        x_path = x_key.to_path(spec, state, symlinks=True)
        y_path = y_key.to_path(spec, state)
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

    @DootKey.kwrap.paths("from")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        target = _from
        base   = target.parent
        target = target.name
        result = sh.fdfind("--color", "never", "-t", "f", "--base-directory",  str(base), ".", target, _return_cmd=True)
        filelist = result.stdout.decode().split("\n")

        printer.info("%s files in %s", len(filelist), target)
        return { _update : filelist }
