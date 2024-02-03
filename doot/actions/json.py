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

@doot.check_protocol
class ReadJson(Action_p):
    """
        Read a .json file and add it to the task state
    """
    _toml_kwargs = [FROM_KEY, UPDATE]

    def __call__(self, spec, task_state:dict):
        data_key = UPDATE.redirect(spec)
        fpath    = FROM_KEY.to_path(spec, task_state)
        with open(fpath) as fp:
            data     = json.load(fp)
        return { data_key : TG.TomlGuard(data) }

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
