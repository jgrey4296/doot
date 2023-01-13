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

import inspect
from doit.cmd_base import NamespaceTaskLoader, opt_cwd, opt_seek_file
from doit.exceptions import InvalidDodoFile
from doit import loader as doit_loader
from doot.utils.checkdir import CheckDir
from doot.utils.loc_data import DootLocData
from doot import default_dooter
from doot.utils.gen_toml import GenToml
from doot.utils.task_group import TaskGroup


#### options related to dooter.py
# select dodo file containing tasks
opt_doot = {
    'section': 'task loader',
    'name': 'dooter',
    'short': 'f',
    'long': 'file',
    'type': str,
    'default': str(default_dooter),
    'env_var': 'DOOT_FILE',
    'help': "load task from doot FILE [default: %(default)s]"
}


class DootLoader(NamespaceTaskLoader):
    """
    Customized Task loader that automatically
    retrieves directory checks, and stores all created tasks
    for later retrieval
    """

    tasks : ClassVar[dict[str,dict]] = []
    cmd_options : ClassVar[tuple]    = (opt_doot, opt_cwd, opt_seek_file)

    def setup(self, opt_values):
        # lazily load namespace from dodo file per config parameters:
        self.namespace = dict(inspect.getmembers(doit_loader.get_module(
            opt_values['dooter'],
            opt_values['cwdPath'],
            opt_values['seek_file'],
        )))

        self.namespace['__doot_all_dirs']   = DootLocData.gen_loc_tasks()
        self.namespace['__doot_all_checks'] = CheckDir.gen_check_tasks()
        self.namespace['__doot_all_tomls']  = GenToml.gen_toml_tasks()

    def load_tasks(self, cmd, pos_args):
        # expand out task groups
        group_tasks = {}
        for x in self.namespace.values():
            if isinstance(x, TaskGroup) and not x.as_creator:
                group_tasks.update(x.to_dict())

        self.namespace.update(group_tasks)
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
