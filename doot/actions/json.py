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

import json
from time import sleep
import sh
import shutil
import tomlguard as TG
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot.enums import ActionResponseEnum
from doot._abstract import Action_p
from doot.structs import DootKey


##-- expansion keys
FROM_KEY           : Final[DootKey] = DootKey.make("from")
UPDATE             : Final[DootKey] = DootKey.make("update_")
##-- end expansion keys

@doot.check_protocol
class ReadJson(Action_p):
    """
        Read a .json file and add it to the task state
    """
    _toml_kwargs = [FROM_KEY, UPDATE]

    @DootKey.kwrap.paths("from")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        fpath    = _from
        with open(fpath) as fp:
            data     = json.load(fp)
        return { _update : TG.TomlGuard(data) }

class ParseJson(Action_p):
    """ parse a string as json """
    pass

class ReadJsonLines(Action_p):
    """ read a .jsonl file, or some of it, and add it to the task state  """

    pass

class WriteJsonLines(Action_p):
    """ Write a list of dicts as a .jsonl file
      optionally gzip the file
      """
    pass

class WriteJson(Action_p):
    """ Write a dict as a .json file  """
    pass
