## base_action.py -*- mode: python -*-
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import shutil
import time
import types
from time import sleep

# ##-- end stdlib imports

# ##-- 3rd party imports
import sh
from jgdv import Mixin, Proto
from jgdv.structs.dkey import DKey, DKeyed

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.errors import LocationError, TaskError, TaskFailed
from doot.mixins.path_manip import PathManip_m

# ##-- end 1st party imports

# ##-| Local
from ..._interface import ActionResponse_e
from .._action import DootBaseAction
from ..util.decorators import IOWriter

# # End of Imports.

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@Mixin(PathManip_m, allow_inheritance=True)
class IOBase(DootBaseAction):
    pass

class AppendAction(IOBase):
    """
      Pre/Ap-pend data from the state to a file
    """
    sep = "\n--------------------\n"

    @DKeyed.args
    @DKeyed.types("sep", fallback=None)
    @DKeyed.paths("to")
    def __call__(self, spec, state, args, sep, to):
        match sep:
            case None:
                sep = AppendAction.sep
            case False:
                sep = None
            case _:
                pass

        loc          = to
        args_keys    = [DKey(x) for x in args]
        exp_args     = [k.expand(spec, state, fallback=None) for k in args_keys]

        if self._is_write_protected(loc):
            raise LocationError("Tried to write a protected location", loc)

        with loc.open('a') as f:
            for arg in exp_args:
                match arg:
                    case None:
                        continue
                    case str():
                        pass
                    case _:
                        arg = str(arg)

                doot.report.wf.act("Append", "%s chars to %s" % (len(arg), loc))
                if sep:
                    f.write(sep)

                f.write(arg)
            else:
                # Done
                pass

class WriteAction(IOBase):
    """
      Writes data from the state to a file, accessed through the
      doot.locs object

    'from' is *not* expanded.
    """

    @DKeyed.redirects("from")
    @DKeyed.paths("to")
    def __call__(self, spec, state, _from, to) -> dict|bool|None:
        data = state[_from]
        match to:
            case None:
                raise LocationError("Can't write to a null location")
            case pl.Path() as x if self._is_write_protected(x):
                raise LocationError("Tried to write a protected location", x)
            case pl.Path() as x:
                loc = x
            case x:
                raise TypeError("Didn't get an appropriate type for a location", x)

        match data:
            case None:
                doot.report.wf.act("Write", "Nothing to Write")
            case _ if not bool(data):
                doot.report.wf.act("Write", "Nothing to Write")
            case [*xs]:
                text = "\n".join(xs)
                loc.write_text(text)
                doot.report.wf.act("Write", "%s chars to %s" % (len(text), loc))
            case bytes():
                doot.report.wf.act("Write", "%s bytes to %s" % (len(data), loc))
                loc.write_bytes(data)
            case str():
                doot.report.wf.act("Write", "%s chars to %s" % (len(data), loc))
                loc.write_text(data)
            case _:
                as_str = str(data)
                doot.report.wf.act("Write", "%s chars to %s" % (len(as_str), loc))
                loc.write_text(as_str)

        return None

class ReadAction(IOBase):
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
        doot.report.wf.act("Read", "%s into %s" % (loc, _update))
        if read_binary:
            with loc.open("rb") as f:
                return { _update : f.read() }

        with loc.open("r") as f:
            match read_lines:
                case "read":
                    return { _update : f.read() }
                case "lines":
                    return { _update : f.readlines() }
                case unk:
                    raise TypeError("Unknown read type", unk)

class CopyAction(IOBase):
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
            raise LocationError("Tried to write a protected location", to)

        match _from:
            case str() | pl.Path():
                expanded = [DKey[pl.Path](_from, fallback=pl.Path(_from)).expand(spec, state)]
            case list():
                expanded = [DKey[pl.Path](x, fallback=pl.Path(x)).expand(spec, state) for x in  _from]
            case _:
                raise doot.errors.ActionError("Unrecognized type for copy sources", _from)

        if len(expanded) > 1 and not dest_loc.is_dir():
                raise doot.errors.ActionError("Tried to copy multiple files to a non-directory")

        for arg in expanded:
            match arg:
                case pl.Path() if "*" in arg.name:
                    if not dest_loc.is_dir():
                        raise doot.errors.ActionError("Tried to copy multiple files to a non-directory")
                    for arg_sub in arg.parent.glob(arg.name):
                        self._validate_source(arg_sub)
                        shutil.copy2(arg_sub, dest_loc)
                case pl.Path():
                    self._validate_source(arg)
                    shutil.copy2(arg, dest_loc)
                case x:
                    raise TypeError("Unexpected Type attempted to be copied")
        else:
            return None

    def _validate_source(self, source:pl.Path) -> None:
        match source:
            case pl.Path() if not source.exists():
                raise doot.errors.ActionError("Tried to copy a file that doesn't exist", source)
            case pl.Path():
                return
            case _:
                raise doot.errors.ActionError("CopyAction expected a path", source)

class MoveAction(IOBase):
    """
      move a file somewhere
      The arguments of the action are held in self.spec
    """

    @DKeyed.paths("from", "to")
    @DKeyed.types("force", check=bool, fallback=False)
    def __call__(self, spec, state, _from, to, force) -> dict|bool|None:
        source     = _from
        dest_loc   = to

        if self._is_write_protected(dest_loc):
            raise LocationError("Tried to write a protected location", dest_loc)
        if not source.exists():
            raise doot.errors.ActionError("Tried to move a file that doesn't exist", source)
        if dest_loc.exists() and not force:
            raise doot.errors.ActionError("Tried to move a file that already exists at the destination", dest_loc)
        if source.is_dir():
            raise doot.errors.ActionError("Tried to move multiple files to a non-directory", source)

        source.rename(dest_loc)
        return None

class DeleteAction(IOBase):
    """
      delete a file / directory specified in spec.args
    """

    @DKeyed.types("recursive", "lax", check=bool, fallback=False)
    def __call__(self, spec, state, recursive, lax):
        rec = recursive
        for arg in spec.args:
            match DKey[pl.Path](arg).expand(spec, state):
                case pl.Path() as loc:
                    pass
                case x:
                    raise TypeError(type(x))
            if self._is_write_protected(loc):
                raise LocationError("Tried to write a protected location", loc)

            if not loc.exists():
                doot.report.wf.act("Delete", "Does Not Exist: %s" % loc)
                continue

            if loc.is_dir() and rec:
                doot.report.wf.act("Delete", "Directory: %s" % loc)
                shutil.rmtree(loc)
            else:
                doot.report.wf.act("Delete", "File: %s" % loc)
                loc.unlink(missing_ok=lax)

class BackupAction(IOBase):
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
            raise LocationError("Tried to write a protected location", dest_loc)

        # ExFat FS has lower resolution timestamps
        # So guard by having a tolerance:
        source_ns       = source_loc.stat().st_mtime_ns
        match dest_loc.exists():
            case True:
                dest_ns  = dest_loc.stat().st_mtime_ns
            case False:
                dest_ns = 1
        source_newer    = source_ns > dest_ns
        difference      = int(max(source_ns, dest_ns) - min(source_ns, dest_ns))
        below_tolerance = difference <= tolerance

        if dest_loc.exists() and ((not source_newer) or below_tolerance):
            return None

        doot.report.wf.act("Backup", "%s -> %s" % (source_loc, dest_loc))
        shutil.copy2(source_loc,dest_loc)
        return None

class EnsureDirectory(IOBase):
    """
      ensure the directories passed as arguments exist
      if they don't, build them
    """

    @DKeyed.args
    def __call__(self, spec, state, args):
        for arg in args:
            loc = DKey[pl.Path](arg).expand(spec, state)
            if not loc.exists():
                doot.report.wf.act("MkDir", str(loc))
            loc.mkdir(parents=True, exist_ok=True)

class UserInput(IOBase):

    @DKeyed.types("prompt", check=str, fallback="?::- ")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, prompt, _update):
        result = input(prompt)
        return { _update : result }

class SimpleFind(IOBase):
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

class TouchFileAction(IOBase):

    @DKeyed.args
    @DKeyed.types("soft", fallback=False)
    def __call__(self, spec, state, args, soft):
        for target in [DKey[pl.Path](x, fallback=None) for x in args]:
            if (target_path:=target.expand(spec, state)) is None:
                continue
            if soft and not target_path.exists():
                continue
            target_path.touch()

class LinkAction(IOBase):
    """
      for x,y in spec.args:
      x.expand().symlink_to(y.expand())

      pass hard=True for a hardlink
    """

    @DKeyed.paths("link", "to", fallback=None)
    @DKeyed.args
    @DKeyed.types("force", "hard", check=bool, fallback=False)
    def __call__(self, spec, state, link, to, args, force, hard):
        if link is not None and to is not None:
            self._do_link(spec, state, spec.kwargs.link, spec.kwargs.to, force, hard=hard)

        for arg in spec.args:
            match arg:
                case [x,y]:
                    self._do_link(spec, state, x,y, force, hard=hard)
                case {"link":x, "to":list() as ys}:
                    raise NotImplementedError()
                case {"link":x, "to":y}:
                    self._do_link(spec, state, x,y, force, hard=hard)
                case {"from":x, "to_rel":y}:
                    raise NotImplementedError()
                case _:
                    raise TypeError("unrecognized link targets")

    def _do_link(self, spec, state, x, y, force, *, hard:bool=False) -> None:
        x_key  = DKey[pl.Path](x)
        y_key  = DKey[pl.Path](y)
        x_path = x_key.expand(spec, state, symlinks=True)
        y_path = y_key.expand(spec, state)
        # TODO when py3.12: use follow_symlinks=False
        if (x_path.exists() or x_path.is_symlink()) and not force:
            logging.warn("SKIP: A Symlink already exists: %s -> %s", x_path, x_path.resolve())
            return
        if not y_path.exists():
            raise doot.errors.ActionError("Link target does not exist", y_path)
        if force and x_path.is_symlink():
            logging.warn("Forcing New Symlink: %s", x_path)
            x_path.unlink()
        if hard:
            x_path.hardlink_to(y_path)
            doot.report.wf.act("Link", "Hard: %s -> %s" % (x_path, y_path))
        else:
            x_path.symlink_to(y_path)
            doot.report.wf.act("Link", "Symbolic: %s -> %s" % (x_path, y_path))

class ListFiles(IOBase):
    """ add a list of all files in a path (recursively) to the state """

    @DKeyed.paths("from")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        target = _from
        base   = target.parent
        target = target.name
        result = sh.fdfind("--color", "never", "-t", "f", "--base-directory",  str(base), ".", target, _return_cmd=True)
        filelist = result.stdout.decode().split("\n")

        doot.report.wf.act("List", "%s files in %s" % (len(filelist), target))
        return { _update : filelist }
