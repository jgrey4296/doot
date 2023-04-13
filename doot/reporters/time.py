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

from collections import defaultdict
import doot
from doot import tasker
from doot.mixins.apis.twitter import TwitterMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin

time_format : Final[str] = doot.config.on_fail("%I:%M %p", str).notify.time_format()
time_voice  : Final[str] = doot.config.on_fail("Moira", str).notify.voice()

class TimeAnnounce(tasker.DootTasker, CommanderMixin):

    def __init__(self, name="say::time", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            "actions" : [self.make_cmd(self.speak_time)],
        })
        return task

    def speak_time(self):
        now     = datetime.datetime.now().strftime(time_format)
        msg     = f"The Time is {now}"
        return ["say", "-v", time_voice, "-r", "50", msg]
