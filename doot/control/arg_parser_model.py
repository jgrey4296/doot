#!/usr/bin/env python3
"""

"""
# ruff: noqa:
# mypy: disable-error-code="attr-defined"
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import atexit#  for @atexit.register
import collections
import contextlib
import datetime
import enum
import faulthandler
import functools as ftz
import hashlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.cli import errors
from jgdv.cli._interface import (EMPTY_CMD, EXTRA_KEY, ArgParserModel_p, ParamSpec_i,
                                 ParamSource_p, ParamSpec_p, ParseResult_d, PositionalParam_p)
from jgdv.cli.param_spec import HelpParam, ParamSpec, SeparatorParam, ParamProcessor
from jgdv.cli import CLIParserModel

# ##-- end 3rd party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
HELP            : Final[ParamSpec]     = HelpParam()
SEPARATOR       : Final[ParamSpec]     = SeparatorParam()
# Body:

@Proto(ArgParserModel_p)
class DootArgParserModel(CLIParserModel):
    """

    # {prog} {args} {cmd} {cmd_args}
    # {prog} {args} [{task} {tasks_args}] - implicit do cmd

    """

    pass
