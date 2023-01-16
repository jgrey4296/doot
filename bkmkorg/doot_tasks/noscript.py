#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
import json
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import doot
from doot.tasker import DootTasker
from doot import globber

def merge_json(target, source, key):
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

class NoScriptMerge(DootTasker):
    """
    merge noscript json files
    """

    def __init__(self, name="noscript::merge", dirs=None):
        super().__init__(name, dirs)

    def task_detail(self, task):
        task.update({
            "actions" : [self.get_and_merge],
            "targets" : [ self.build / "noscript_merged.json" ],
        })
        return task

    def get_and_merge(self, targets):
        final = defaultdict(lambda: {})

        for target in self.dirs.src.glob("noscript*.json"):
            data = json.loads(target.read_text())

            for key in data:
                merge_json(final, data, key)

        for site in final['policy']['sites']['trusted']:
            assert(site not in final['policy']['sites']['untrusted']), site

        print("Final Sizes: ")
        print(f"Trusted Sites: {len(final['policy']['sites']['trusted'])}")
        print(f"UnTrusted Sites: {len(final['policy']['sites']['untrusted'])}")
        pl.Path(targets[0]).write_text(json.dumps(final, indent=4, sort_keys=True, ensure_ascii=False))
