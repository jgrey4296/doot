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
##-- end logging

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

COMP_TAR_CMD  = sh.tar.bake("-cf", "-")
COMP_GZIP_CMD = sh.gzip.bake("--best")
DECOMP_CMD    = sh.tar.bake("-xf")

@doot.check_protocol
class TarCompressAction(Action_p):
    """ Compresses a target into a .tar.gz file """

    @DootKey.kwrap.paths("file")
    @DootKey.kwrap.paths("to", hint={"on_fail":None})
    def __call__(self, spec, state, file, to):
        target = file
        output = to or target.with_suffix(target.suffix + ".tar.gz")

        if output.exists():
            raise doot.errors.DootActionError("Compression target already exists")
        if target.is_dir():
            COMP_GZIP_CMD(_in=COMP_TAR_CMD("-C", target, ".", _piped=True), _out=output)
        else:
            COMP_GZIP_CMD(_in=COMP_TAR_CMD("-C", target.parent, target.name, _piped=True), _out=output)

@doot.check_protocol
class TarDecompressAction(Action_p):
    """ Decompresses a .tar.gz file """

    @DootKey.kwrap.paths("file", "to")
    def __call__(self, spec, state, file, to):
        target = file
        output = to
        if not ".tar.gz" in target.name:
            printer.warning("Decompression target isn't a .tar.gz", target)
            return ActionResponseEnum.FAIL

        DECOMP_CMD(target, "-C", output)


@doot.check_protocol
class TarListAction(Action_p):
    """ List the contents of a tar archive """

    @DootKey.kwrap.paths("from")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        target = _from
        if "".join(target.suffixes) != ".tar.gz":
            printer.warning("Trying to list the contents of a non-tar archive")
            return ActionResponseEnum.FAIL

        result = sh.tar("--list", "-f", str(target))
        lines = result.split("\n")
        return { _update : lines }


class ZipNewAction(Action_p):
    """ Make a new zip archive """
    pass

class ZipAddAction(Action_p):
    """ Add a file/directory to a zip archive """
    pass

class ZipGetAction(Action_p):
    """ unpack a file/files/all files from a zip archive """
    pass

class ZipListAction(Action_p):
    """ List the contents of a zip archive """
    pass
