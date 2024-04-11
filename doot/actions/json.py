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

import math
import json
from time import sleep
import sh
import shutil
import jsonlines
import tomlguard as TG
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot.enums import ActionResponseEnum
from doot._abstract import Action_p
from doot.structs import DootKey


##-- expansion keys
FROM_KEY           : Final[DootKey] = DootKey.build("from")
UPDATE             : Final[DootKey] = DootKey.build("update_")
##-- end expansion keys

class ReadJson(Action_p):
    """
        Read a .json file and add it to the task state as a tomlguard
    """
    _toml_kwargs = [FROM_KEY, UPDATE]

    @DootKey.dec.paths("from")
    @DootKey.dec.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        if _from.suffix != ".json":
            printer.warning("Read Json expected a .json file, got: %s", _from)

        with open(_from) as fp:
            data     = json.load(fp)
        return { _update : TG.TomlGuard(data) }

class ParseJson(Action_p):
    """ parse a string as json """

    @DootKey.dec.types("from")
    @DootKey.dec.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        return { _update : json.loads(_from) }

class ReadJsonLines(Action_p):
    """ read a .jsonl file, or some of it, and add it to the task state  """

    @DootKey.dec.paths("from")
    @DootKey.dec.types("offset", hint={"default":0})
    @DootKey.dec.types("count", hint={"default":math.inf})
    @DootKey.dec.redirects("update_")
    def __call__(self, spec, state, _from, offset, count, _update):
        if _from.suffix != ".jsonl":
            printer.warning("Read JsonNL expects a .jsonl file, got: %s", _from)

        result = []
        target_end = offset + count
        with jsonlines.open(_from) as reader:
            for i, obj in enumerate(reader):
                if i < offset:
                    continue
                result.append(obj)
                if target_end <= i:
                    break

        return { _update : result }


class WriteJsonLines(Action_p):
    """ Write a list of dicts as a .jsonl file
      optionally gzip the file
    """

    @DootKey.dec.types("from")
    @DootKey.dec.paths("to")
    def __call__(self, spec, state, _from, _to):
        if _to.suffix != ".jsonl":
            printer.warning("Write Json Lines expected a .jsonl file, got: %s", _to)

        with jsonlines.open(_to, mode='a') as writer:
            writer.write(_from)


class WriteJson(Action_p):
    """ Write a dict as a .json file  """

    @DootKey.dec.types("from")
    @DootKey.dec.paths("to")
    def __call__(self, spec, state, _from, _to):
        if _to.suffix != ".json":
            printer.warning("Write Json Expected a .json file, got: %s", _to)
        with open(_to, mode='w') as writer:
            json.dump(_from,
                      writer,
                      ensure_ascii=True,
                      indent=4,
                      sort_keys=True)
