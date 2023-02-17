#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import datetime
import enum
import fileinput
import functools as ftz
import itertools as itz
import logging as logmod
import os
import pathlib as pl
import re
import shutil
import sys
import time
import types
import zipfile
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from random import randint
from time import sleep
from types import FunctionType, MethodType
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

from doit.action import CmdAction
from doit.task import Task as DoitTask
from doit.task import dict_to_task
from doit.tools import Interactive

from doot.errors import DootDirAbsent
from doot.utils.general import ForceCmd

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doit.exceptions import TaskFailed
import doot
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.zipper import ZipperMixin
from doot.mixins.batch import BatchMixin

class ActionsMixin(CommanderMixin, FilerMixin):
    """
    Utility Mixin that combines command and file methods
    """

    def get_uuids(self, *args):
        raise NotImplementedError()

    def edit_by_line(self, files:list[pl.Path], fn, inplace=True):
        for line in fileinput(files=files, inplace=inplace):
            fn(line)

