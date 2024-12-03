#!/usr/bin/env python3
"""


"""

# Imports:
##-- builtin imports
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import shutil
import time
import types
import weakref
from time import sleep
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import sh

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract import Action_p
from doot.enums import ActionResponse_e
from doot.errors import DootTaskError, DootTaskFailed
from doot.mixins.zipper import Zipper_m
from doot.structs import DKey, DKeyed

# ##-- end 1st party imports

##-- end builtin imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

COMP_TAR_CMD  = sh.tar.bake("-cf", "-")
COMP_GZIP_CMD = sh.gzip.bake("--best")
DECOMP_CMD    = sh.tar.bake("-xf")

class TarCompressAction(Action_p):
    """ Compresses a target into a .tar.gz file """

    @DKeyed.paths("file")
    @DKeyed.paths("to", fallback=None)
    def __call__(self, spec, state, file, to):
        target = file
        output = to or target.with_suffix(target.suffix + ".tar.gz")

        if output.exists():
            raise doot.errors.DootActionError("Compression target already exists")
        if target.is_dir():
            COMP_GZIP_CMD(_in=COMP_TAR_CMD("-C", target, ".", _piped=True), _out=output)
        else:
            COMP_GZIP_CMD(_in=COMP_TAR_CMD("-C", target.parent, target.name, _piped=True), _out=output)

class TarDecompressAction(Action_p):
    """ Decompresses a .tar.gz file """

    @DKeyed.paths("file", "to")
    def __call__(self, spec, state, file, to):
        target = file
        output = to
        if not ".tar.gz" in target.name:
            printer.warning("Decompression target isn't a .tar.gz", target)
            return ActionResponse_e.FAIL

        DECOMP_CMD(target, "-C", output)

class TarListAction(Action_p):
    """ List the contents of a tar archive """

    @DKeyed.paths("from")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        target = _from
        if "".join(target.suffixes) != ".tar.gz":
            printer.warning("Trying to list the contents of a non-tar archive")
            return ActionResponse_e.FAIL

        result = sh.tar("--list", "-f", str(target))
        lines = result.split("\n")
        return { _update : lines }

class ZipNewAction(Zipper_m, Action_p):
    """ Make a new zip archive """

    @DKeyed.paths("target")
    def __call__(self, spec, state, target):
         self.zip_create(target)

class ZipAddAction(Zipper_m, Action_p):
    """ Add a file/directory to a zip archive """

    @DKeyed.paths("target")
    @DKeyed.args
    def __call__(self, spec, state, target, args):
        arg_paths = []
        for str in args:
            key = DKey(x, mark=DKey.mark.PATH)
            match key.expand(spec, state, on_fail=None):
                case pl.Path() as x if not x.exists():
                    printer.warning("Can't add non-existent path to zip: %s", key)
                case pl.Path() as x:
                    arg_paths.append(x)
                case _:
                    printer.warning("Can't add non-expandable path to zip: %s", key)

        self.zip_add_paths(target, *arg_paths)

class ZipGetAction(Zipper_m, Action_p):
    """ unpack a file/files/all files from a zip archive """

    @DKeyed.paths("zipf", "target")
    def __call__(self, spec, state, zipf:pl.Path, target:pl.Path):
        if target.is_file():
            raise doot.errors.DootActionError("Can't unzip to a file: %s", target)

        self.zip_unzip_to(target, zipf)

class ZipListAction(Action_p):
    """ List the contents of a zip archive """

    @DKeyed.paths("target")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, target:pl.Path, _update):
        contents = self.zip_get_contents(target)
        printer.info("Contents of Zip File: %s", target)
        for x in contents:
            printer.info("- %s", x)
        printer.info("--")

        if _update == "update_":
            return

        return { _update : contents }
