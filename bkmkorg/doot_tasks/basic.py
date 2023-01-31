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
from doot import tasker, task_mixins

time_format : Final = doot.config.on_fail("%I:%M %p", str).tool.doot.announce.time_format()
time_voice  : Final = doot.config.on_fail("Moira", str).tool.doot.announce.voice()

class TimeAnnounce(tasker.DootTasker, task_mixins.ActionsMixin):

    def __init__(self, name="say::time", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            self.cmd(self.speak_time),
        })
        return task

    def speak_time(self):
        now     = datetime.now().strftime(time_format)
        msg     = f"The Time is {now}"
        return ["say", "-v", "Moira", "-r", "50", msg]

class NoScriptMerge(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    merge noscript json files
    """

    def __init__(self, name="noscript::merge", locs=None):
        super().__init__(name, locs)
        self.master_data = defaultdict(lambda: {})
        assert(self.locs.src)
        assert(self.locs.temp)

    def task_detail(self, task):
        srcs   = self.locs.src.glob("noscript*.json")
        target = self.locs.build / "noscript_merged.json"
        task.update({
            "actions" : [
                (self.copy_to, [self.locs.temp, target], {"fn": "backup"}),
                self.get_and_merge,
                lambda: {"json": json.dumps(self.master_data, indent=4, sort_keys=True, ensure_ascii=False)},
                (self.write_to, [target, "json"]),
                self.report_on_data,
            ],
            "targets" : [ target ],
        })
        return task

    def get_and_merge(self, srcs):
        for src in srcs:
            data = json.loads(target.read_text())

            for key in data:
                self.merge_json(self.master_data, data, key)

        for site in final['policy']['sites']['trusted']:
            assert(site not in self.master_data['policy']['sites']['untrusted']), site

    def report_on_data(self):
        print("Final Sizes: ")
        print(f"Trusted Sites: {len(self.master_data['policy']['sites']['trusted'])}")
        print(f"UnTrusted Sites: {len(self.master_data['policy']['sites']['untrusted'])}")

    def merge_json(self, target, source, key):
        """
        dfs over a specific key in the source,
        copying into target
        """
        queue = [(target, source, key)]

        while bool(queue):
            current = queue.pop()
            print(f"Merging: {current[2]}")
            targ = current[0][current[2]]
            sour = current[1][current[2]]

            match (targ, src):
                case dict(), dict():
                    for key in src.keys():
                        if key not in targ:
                            targ[key] = src[key]
                        else:
                            queue += [(targ, src, key)]
                case list(), list():
                    print(f"Merging Lists: {len(targ)} : {len(src)}")
                    now_set = set(targ)
                    now_set.update(src)
                    print(f"Updated Length: {len(now_set)}")
                    targ.clear()
                    targ.extend(now_set)
                case bool(), bool() if targ != src:
                    print(f"{current[2]} Conflict: {targ}, {src}")
                    result = input(f"Enter for {targ}, else {src}")
                    if not bool(result):
                        current[0][current[2]] = targ
                    else:
                        current[0][current[2]] = src
                case bool(), bool():
                    pass
