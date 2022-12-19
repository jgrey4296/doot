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
from doot.utils.task_group import TaskGroup

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

__all__ = [
    "pip_group"
]


##-- pdf
from doot.builders import pdf
pdf_group = TaskGroup("pdf_group",

                      )
##-- end pdf

##-- python
python_group = TaskGroup("python",

                         )

##-- end python

##-- poetry
from doot.builders import poetry_install as poetry
poetry_group = TaskGroup("poetry_group",
                         poetry.install,
                         poetry.wheel,
                         poetry.requirements)

##-- end poetry

##-- conda
from doot.builders import conda
conda_group = TaskGroup("conda_group",

                        )
##-- end conda

##-- erlang
from doot.builders import erlang
erlang_group = TaskGroup("erlang_group",

                        )
##-- end erlang

##-- ruby
from doot.builders import gems
ruby_group = TaskGroup("ruby_group",

                       )
##-- end ruby

##-- godot
from doot.builders import godot
godot_group = TaskGroup("godot_group",

                        )
##-- end godot

##-- grunt
from doot.builders import grunt
grunt_group = TaskGroup("grunt group",

                        )
##-- end grunt

##-- homebrew
from doot.builders import homebrew
brew_group = TaskGroup("brew group",

                       )
##-- end homebrew


##-- xml
xml_group = TaskGroup("xml_group",

                      )
##-- end xml

##-- json
json_group = TaskGroup("json group",

                       )
##-- end json

##-- plantuml
from doot.docs import plantuml
plantuml_group = TaskGroup("plantuml_group",

                           )
##-- end plantuml
