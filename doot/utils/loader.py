#!/usr/bin/env python3
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

from doit.cmd_base import DodoTaskLoader
from doit import loader as doit_loader

class DootLoader(DodoTaskLoader):

    tasks : ClassVar[dict[str,dict]] = []

    def load_tasks(self, cmd, pos_args):
        tasks = doit_loader.load_tasks(
            self.namespace, self.cmd_names, allow_delayed=cmd.execute_tasks,
            args=pos_args, config=self.config, task_opts=self.task_opts)

        # Add task options from config, if present
        if self.config is not None:
            for task in tasks:
                task_stanza = 'task:' + task.name
                if task_stanza in self.config:
                    task.cfg_values = self.config[task_stanza]

        # add values from API run_tasks() usage
        if self.task_opts is not None:
            for task in tasks:
                if self.task_opts and task.name in self.task_opts:
                    task.cfg_values = self.task_opts[task.name]
                    if task.pos_arg and task.pos_arg in task.cfg_values:
                        task.pos_arg_val = task.cfg_values[task.pos_arg]

        DootLoader.tasks = tasks
        return tasks
