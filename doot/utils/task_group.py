#/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
import re
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

clean_re = re.compile("\s+")

class TaskGroup:
    """ A Group of task specs, none of which require params
    Can contain: dicts, objects with a `build` method,
    objects with `create_doit_tasks`, and callables
    """


    def __init__(self, name, *args):
        self.create_doit_tasks = self.build
        self.name              = clean_re.sub("_", name)
        self.tasks             = args

    def build(self):
        for task in self.tasks:
            result = task
            match task:
                case dict():
                    pass
                case x if hasattr(x, "build"):
                    result = task.build()
                case x if hasattr(x, "create_doit_tasks"):
                    result = task.create_doit_tasks()
                case x if callable(x):
                    result = task()


            if result is not None:
                yield result

        if any(hasattr(x, 'gen_toml') for x in self.tasks):
            GenToml.add_generator(self.name, self.gen_toml)


        return { "basename" : "_" + self.name,
                 "actions" : [],
                }


    def gen_toml(self, dependencies):
        """
        Insert any task's required toml data into a top level
        file for customisation
        """

        total_toml = []
        for task in [x for x in self.tasks if hasattr(x, "gen_toml")]:
            total_toml.append(task.gen_toml())

        with open(dependencies[0], 'a') as f:
            f.write("\n".join(total_toml))




class GenToml:
    generators : ClassVar[dict] = {}

    @staticmethod
    def add_generator(name : str, gen : Callable):
        GenToml.generators[name] = gen

    def __init__(self):
        self.create_doit_tasks = self.build
        self.name = "gen-toml"
        self.gen_file = pl.Path("gen_toml.toml")

    def build(self):
        yield {
            "basename" : "gen-toml",
            "name"     : "prep",
            "actions"  : [ self.prep_gen_toml ],
            "targets"  : [ self.gen_file ],
            "clean"    : True,
        }

        for name, gen in GenToml.generators.items():
            yield {
                "basename" : "gen-toml",
                "name"     : name,
                "actions"  : [ gen ],
                "file_dep" : [self.gen_file],
            }

    def prep_gen_toml(self):
        self.gen_file.unlink(missing_ok=True)

        text = ["## Generated default toml data",
                "## copy this into your",
                "## pyproject/cargo/doot . toml file",
                ""]
        self.gen_file.write_text("\n".join(text))
