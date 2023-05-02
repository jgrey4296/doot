#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doit.doit_cmd import DoitMain
from doit.cmd_help import Help
from doit.cmd_run import Run
from doit.cmd_clean import Clean
from doit.cmd_info import Info
from doit.cmd_forget import Forget
from doit.cmd_ignore import Ignore
from doit.cmd_dumpdb import DumpDB
from doit.cmd_strace import Strace
from doit.cmd_completion import TabCompletion
from doit.cmd_resetdep import ResetDep

from doot.core.cmds.list_cmd import ListCmd

class DootMain(DoitMain):
    DOIT_CMDS = (Help, Run, ListCmd, Info, Clean, Forget, Ignore, DumpDB,
                 Strace, TabCompletion, ResetDep)
