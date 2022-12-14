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
from importlib.resources import files
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

##-- data
data_path = files("doot.__templates")
doot_file = data_path.joinpath("dooter_template.py")
doot_text = doot_file.read_text()
##-- end data


def task_stub_dooter():
    def make_dooter(targets):
        if pl.Path(targets[0]).exists():
            return True

        with open(targets[0], 'a') as f:
            f.write(doot_text)

    return {
        "actions" : [make_dooter],
        "targets" : ["dooter.py"],
    }
