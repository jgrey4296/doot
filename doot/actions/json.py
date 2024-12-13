#!/usr/bin/env python3
"""


"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import json
import logging as logmod
import math
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
import jsonlines
import sh
from jgdv.structs.chainguard import ChainGuard
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract import Action_p
from doot.enums import ActionResponse_e
from doot.errors import DootTaskError, DootTaskFailed
from doot.structs import DKey, DKeyed

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

class ReadJson(Action_p):
    """
        Read a .json file and add it to the task state as a ChainGuard
    """

    @DKeyed.paths("from")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        if _from.suffix != ".json":
            printer.warning("Read Json expected a .json file, got: %s", _from)

        with open(_from) as fp:
            data     = json.load(fp)
        return { _update : ChainGuard(data) }

class ParseJson(Action_p):
    """ parse a string as json """

    @DKeyed.types("from")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        return { _update : json.loads(_from) }

class ReadJsonLines(Action_p):
    """ read a .jsonl file, or some of it, and add it to the task state  """

    @DKeyed.paths("from")
    @DKeyed.types("offset", fallback=0)
    @DKeyed.types("count", fallback=math.inf)
    @DKeyed.redirects("update_")
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

    @DKeyed.types("from")
    @DKeyed.paths("to")
    def __call__(self, spec, state, _from, _to):
        if _to.suffix != ".jsonl":
            printer.warning("Write Json Lines expected a .jsonl file, got: %s", _to)

        with jsonlines.open(_to, mode='a') as writer:
            writer.write(_from)

class WriteJson(Action_p):
    """ Write a dict as a .json file  """

    @DKeyed.types("from")
    @DKeyed.paths("to")
    def __call__(self, spec, state, _from, _to):
        if _to.suffix != ".json":
            printer.warning("Write Json Expected a .json file, got: %s", _to)
        with open(_to, mode='w') as writer:
            json.dump(_from,
                      writer,
                      ensure_ascii=True,
                      indent=4,
                      sort_keys=True)
