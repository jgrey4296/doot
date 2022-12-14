#/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
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


# file -I {}
# iconv -f {enc} -t {enc} {} > conv-{}
class UTF8EncodeTask:

    def __init__(self, globs, encoding="utf8", name="default", **kwargs):
        self.create_doit_tasks = self.build
        self.globs             = globs
        self.kwargs            = kwargs
        self.default_spec      = { "basename" : f"utf8::{name}" }
        self.encoding          = encoding

    def convert(self):
        base = pl.Path(".")
        for glob in globs:
            for fpath in base.glob(glob):
                if not fpath.is_file():
                    continue


    def build(self):
        raise NotImplementedError()
        task_desc = self.default_spec.copy()
        task_desc.update(self.kwargs)
        task_desc.update({
            "actions"  : [ self.mkdir ],
        })
        return task_desc


