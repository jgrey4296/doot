#!/usr/bin/env python3
"""
Cmd experiment based on doit-graph
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

# from doit.cmd_base import DoitCmdBase
from doit.cmd_run import Run as DoitRun
# from doit.control import TaskControl


class DootRun(DoitRun):
    """
    Simple override of run,
    changing default reporter
    """
    name = "custom_run"


    def _execute(self, outfile,
                 verbosity=None, always=False, continue_=False,
                 reporter='custom', num_process=0, par_type='process',
                 single=False, auto_delayed_regex=False, force_verbosity=False,
                 failure_verbosity=0, pdb=False):
        if reporter == "console":
            reporter = "custom"
        super()._execute(outfile,
                 verbosity, always, continue_,
                 reporter, num_process, par_type,
                 single, auto_delayed_regex, force_verbosity,
                 failure_verbosity, pdb)
