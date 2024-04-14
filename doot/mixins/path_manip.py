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
# import more_itertools as mitz
# from boltons import
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot
from doot.structs import DootKey
from doot.enums import LoopControl, LocationMeta

MARKER : Final[str] = doot.constants.paths.MARKER_FILE_NAME
walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()

class PathManip_m:
    """
      A Mixin for common path manipulations
    """

    def _calc_path_parts(self, fpath, roots) -> dict:
        """ take a path, and get a dict of bits to add to state from it """
        assert(fpath is not None)

        temp_stem  = fpath
        # This handles "a/b/c.tar.gz"
        while temp_stem.stem != temp_stem.with_suffix("").stem:
            temp_stem = temp_stem.with_suffix("")

        return {
            'rpath'   : self._get_relative(fpath, roots),
            'fstem'   : temp_stem.stem,
            'fparent' : fpath.parent,
            'fname'   : fpath.name,
            'fext'    : fpath.suffix,
            'pstem'   : fpath.parent.stem,
            }

    def _build_roots(self, spec, state, roots) -> list[pl.Path]:
        """
        convert roots from keys to paths
        """
        roots = roots or []
        results = []

        for root in roots:
            root_key = DootKey.build(root, explicit=True)
            results.append(root_key.to_path(spec, state))

        return results

    def _get_relative(self, fpath, roots) -> pl.Path:
        logging.debug("Finding Relative Path of: %s using %s", fpath, roots)
        if not fpath.is_absolute():
            return fpath

        if not bool(roots):
            return None

        for root_path in roots:
            try:
                return fpath.relative_to(root_path)
            except ValueError:
                continue

        raise ValueError(f"{fpath} is not able to be made relative", roots)

    def _shadow_path(self, rpath:pl.Path, shadow_root:pl.Path) -> pl.Path:
        """ take a relative path, apply it onto a root to create a shadowed location """
        assert(isinstance(rpath, pl.Path))
        assert(not rpath.is_absolute())
        result      = shadow_root / rpath
        if result == doot.locs[rpath]:
            raise doot.errors.DootLocationError("Shadowed Path is same as original", fpath)

        return result.parent

    def _find_parent_marker(self, fpath, marker=None) -> None|pl.Path:
        """ Go up the parent list to find a marker file, return the dir its in """
        marker = marker or MARKER
        for p in fpath.parents:
            if (p / marker).exists():
                return p

        return None

    def _is_write_protected(self, fpath) -> bool:
        for key in filter(lambda x: doot.locs.metacheck(x, LocationMeta.protected), doot.locs):
            base = getattr(doot.locs, key)
            if fpath.is_relative_to(base):
                return True

        return False

    def _normalize(self, path:pl.Path, root=None, symlinks:bool=False) -> pl.Path:
        """
          a basic path normalization
          expands user, and resolves the location to be absolute
        """
        result = path
        if symlinks:
            logging.warning("TODO normalize path with symlinks")
        match result.parts:
            case ["~", *xs]:
                result = result.expanduser().resolve()
            case ["/", *xs]:
                result = result
            case _ if root:
                result = (root / path).expanduser().resolve()
            case _:
                pass

        return result

class Walker_m:
    """ A Mixin for walking directories,
      written for py<3.12
      """
    control_e = LoopControl

    def walk_all(self, roots, exts, rec=False, fn=None) -> Generator[dict]:
        """
        walk all available targets,
        and generate unique names for them
        """
        result = []
        match rec:
            case True:
                for root in roots:
                    result += self.walk_target_deep(root, exts, fn)
            case False:
                for root in roots:
                    result += self.walk_target_shallow(root, exts, fn)

        return result

    def walk_target_deep(self, target, exts, fn) -> Generator[pl.Path]:
        logging.info("Deep Walking Target: %s : exts=%s", target, exts)
        if not target.exists():
            return None

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
            match fn(current):
                case self.control_e.yes:
                    yield current
                case True if current.is_dir():
                    queue += sorted(current.iterdir())
                case True | self.control_e.yesAnd:
                    yield current
                    if current.is_dir():
                        queue += sorted(current.iterdir())
                case False | self.control_e.noBut if current.is_dir():
                    queue += sorted(current.iterdir())
                case None | False:
                    continue
                case self.control_e.no | self.control_e.noBut:
                    continue
                case _ as x:
                    raise TypeError("Unexpected filter value", x)

    def walk_target_shallow(self, target, exts, fn):
        logging.debug("Shallow Walking Target: %s", target)
        if target.is_file():
            fn_fail = fn(target) in [None, False, self.control_e.no, self.control_e.noBut]
            ignore  = target.name in walk_ignores
            bad_ext = (bool(exts) and (x.is_file() and x.suffix in exts))
            if not (fn_fail or ignore or bad_ext):
                yield target
            return None

        for x in target.iterdir():
            fn_fail = fn(x) in [None, False, self.control_e.no, self.control_e.noBut]
            ignore  = x.name in walk_ignores
            bad_ext = bool(exts) and x.is_file() and x.suffix not in exts
            if not (fn_fail or ignore or bad_ext):
                yield x
