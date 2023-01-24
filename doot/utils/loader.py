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

from types import FunctionType, MethodType
from collections import OrderedDict
import inspect
from doit.cmd_base import NamespaceTaskLoader, opt_cwd, opt_seek_file
from doit.exceptions import InvalidDodoFile
from doit import loader as doit_loader

from doot.loc_data import DootLocData
import doot
from doot.utils.gen_toml import GenToml
from doot.task_group import TaskGroup
from doot.utils.dir_tasks import CheckDir

TASK_STRING = "task_"

#### options related to dooter.py
# select dodo file containing tasks
opt_doot = {
    'section': 'task loader',
    'name': 'dooter',
    'short': 'f',
    'long': 'file',
    'type': str,
    'default': str(doot.default_dooter),
    'env_var': 'DOOT_FILE',
    'help': "load task from doot FILE [default: %(default)s]"
}

class DootLoader(NamespaceTaskLoader):
    """
    Customized doit_loader.Task loader that automatically
    retrieves directory checks, and stores all created tasks
    for later retrieval
    """

    cmd_options : ClassVar[tuple]    = (opt_doot, opt_cwd, opt_seek_file)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_list = []

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


    def load_doit_config(self):
        return doot.config.get_table()


    def load_tasks(self, cmd, pos_args):
        self.expand_task_groups()
        logging.info("Creating Tasks")
        self._load_tasks(self.namespace, self.cmd_names, allow_delayed=cmd.execute_tasks, args=pos_args, config=self.config, task_opts=self.task_opts)

        logging.info("Tasks: %s", self.task_list)

        # Add task options from config, if present
        if self.config is not None:
            for task in self.task_list:
                task_stanza = 'task:' + task.name
                if task_stanza in self.config:
                    task.cfg_values = self.config[task_stanza]

        # add values from API run_tasks() usage
        if self.task_opts is not None:
            for task in self.task_list:
                if self.task_opts and task.name in self.task_opts:
                    task.cfg_values = self.task_opts[task.name]
                    if task.pos_arg and task.pos_arg in task.cfg_values:
                        task.pos_arg_val = task.cfg_values[task.pos_arg]

        return self.task_list

    def expand_task_groups(self):
        group_tasks = {}
        for x in self.namespace.values():
            if isinstance(x, TaskGroup) and not x.as_creator and bool(x):
                logging.info("Expanding: %s", x)
                group_tasks.update(x.to_dict())

        logging.debug("Total Expanded Tasks: %s", list(x for x in group_tasks.keys()))
        self.namespace.update(group_tasks)

    def _load_tasks(self, namespace, command_names=(), allow_delayed=False, args=(), config=None, task_opts=None):
        """
        Reimplementation of doit.loader.load_tasks
        """
        funcs = self._get_task_creators(namespace, command_names)
        # sort by the order functions were defined (line number)
        # TODO: this ordering doesnt make sense when generators come
        # from different modules
        funcs.sort(key=lambda obj: obj[2])

        # Map arg_name to its position.
        # Save only args that do not start with `-` (potentially task names)
        arg_pos = {}
        for index, term in enumerate(args):
            if term[0] != '-':
                arg_pos[term] = index

        for name, ref, _ in funcs:
            self.current_name = name
            delayed = getattr(ref, 'doit_create_after', None)

            # Parse command line arguments for task generator parameters
            creator_params = getattr(ref, '_task_creator_params', None)
            if creator_params is not None:
                parser = doit_loader.TaskParse([doit_loader.CmdOption(opt) for opt in creator_params])
                # Add task options from config, if present
                if config:
                    task_stanza = 'task:' + name
                    if task_stanza in config:
                        parser.overwrite_defaults(config[task_stanza])

                # option params passed through API
                if task_opts and name in task_opts:
                    creator_kwargs = task_opts[name]
                # if relevant command line defaults are available parse those
                elif name in arg_pos:
                    creator_kwargs, _ = parser.parse(args[arg_pos[name] + 1:])
                else:
                    creator_kwargs, _ = parser.parse('')
            else:
                creator_kwargs = {}

            if not delayed:  # not a delayed task, just run creator
                self._process_gen(ref, creator_kwargs)
            elif delayed.creates:  # delayed with explicit task basename
                for tname in delayed.creates:
                    self._add_delayed(tname, ref, delayed, creator_kwargs)
            elif allow_delayed:  # delayed no explicit name, cmd run
                self._add_delayed(name, ref, delayed, creator_kwargs)
            else:  # delayed no explicit name, cmd list (run creator)
                self._process_gen(ref, creator_kwargs)

    def _get_task_creators(self, namespace, command_names):
        """get functions defined in the `namespace` and select the task-creators

        A task-creator is a function that:
        - name starts with the string TASK_STRING
        - has the attribute `create_doit_tasks`

        @return (list - func) task-creators
        """
        funcs = []
        prefix_len = len(TASK_STRING)
        # get all functions that are task-creators
        for name, ref in namespace.items():

            # Do not solicit tasks from the @self.task_params decorator.
            if ref is doit_loader.task_params:
                continue

            # function is a task creator because of its name
            if name.startswith(TASK_STRING) and isinstance(ref, (FunctionType, MethodType)):
                # remove TASK_STRING prefix from name
                task_name = name[prefix_len:]

            # object is a task creator because it contains the special method
            elif hasattr(ref, 'create_doit_tasks'):
                ref = ref.create_doit_tasks
                # create_doit_tasks might have a basename to overwrite task name.
                task_name = getattr(ref, 'basename', name)

            # ignore functions that are not a task creator
            else:  # pragma: no cover
                # coverage can't get "else: continue"
                continue

            # tasks can't have the same name of a commands
            if task_name in command_names:
                msg = (f"doit_loader.Task can't be called '{task_name}' because this is a command name."
                    " Please choose another name.")
                raise doit_loader.InvalidDodoFile(msg)
            # get line number where function is defined
            line = inspect.getsourcelines(ref)[1]
            # add to list task generator functions
            funcs.append((task_name, ref, line))

        return funcs

    def _generate_task_from_return(self, func_name, task_dict, gen_doc):
        """generate a single task from a dict returned by a task generator"""
        if 'name' in task_dict:
            raise InvalidTask("doit_loader.Task '%s'. Only subtasks use field name." %
                            func_name)

        task_dict['name'] = task_dict.pop('basename', func_name)

        # Use task generator docstring
        # if no doc present in task dict
        if 'doc' not in task_dict:
            task_dict['doc'] = gen_doc

        return doit_loader.dict_to_task(task_dict)

    def _generate_task_from_yield(self, tasks, func_name, task_dict, gen_doc):
        """generate a single task from a dict yielded by task generator

        @param tasks: dictionary with created tasks
        @return None: the created task is added to 'tasks' dict
        """
        # check valid input
        if not isinstance(task_dict, dict):
            raise InvalidTask("doit_loader.Task '%s' must yield dictionaries" %
                            func_name)

        msg_dup = "doit_loader.Task generation '%s' has duplicated definition of '%s'"
        basename = task_dict.pop('basename', None)
        # if has 'name' this is a sub-task
        if 'name' in task_dict:
            basename = basename or func_name
            # if subname is None attributes from group task
            if task_dict['name'] is None:
                task_dict['name'] = basename
                task_dict['actions'] = None
                group_task = doit_loader.dict_to_task(task_dict)
                group_task.has_subtask = True
                tasks[basename] = group_task
                return

            # name is '<task>.<subtask>'
            full_name = f"{basename}:{task_dict['name']}"
            if full_name in tasks:
                raise InvalidTask(msg_dup % (func_name, full_name))
            task_dict['name'] = full_name
            sub_task = doit_loader.dict_to_task(task_dict)
            sub_task.subtask_of = basename

            # get/create task group
            group_task = tasks.get(basename)
            if group_task:
                if not group_task.has_subtask:
                    raise InvalidTask(msg_dup % (func_name, basename))
            else:
                group_task = doit_loader.Task(basename, None, doc=gen_doc, has_subtask=True)
                tasks[basename] = group_task
            group_task.task_dep.append(sub_task.name)
            tasks[sub_task.name] = sub_task
        # NOT a sub-task
        else:
            if not basename:
                raise InvalidTask(
                    "doit_loader.Task '%s' must contain field 'name' or 'basename'. %s" %
                    (func_name, task_dict))
            if basename in tasks:
                raise InvalidTask(msg_dup % (func_name, basename))
            task_dict['name'] = basename
            # Use task generator docstring if no doc present in task dict
            if 'doc' not in task_dict:
                task_dict['doc'] = gen_doc
            tasks[basename] = doit_loader.dict_to_task(task_dict)

    def _generate_tasks(self, func_name, gen_result, gen_doc=None):
        """Create tasks from a task generator result.

        @param func_name: (string) name of taskgen function
        @param gen_result: value returned by a task generator function
                        it can be a dict or generator (generating dicts)
        @param gen_doc: (string/None) docstring from the task generator function
        @param param_def: (dict) additional task parameter definitions
                        passed down from generator
        @return: (list - doit_loader.Task)
        """
        # a task instance, just return it without any processing
        if isinstance(gen_result, doit_loader.Task):
            return (gen_result,)

        # task described as a dictionary
        if isinstance(gen_result, dict):
            return [self._generate_task_from_return(func_name, gen_result, gen_doc)]

        # a generator
        if inspect.isgenerator(gen_result):
            tasks = OrderedDict()  # task_name: task
            # the generator return subtasks as dictionaries
            for task_dict, x_doc in doit_loader.flat_generator(gen_result, gen_doc):
                if isinstance(task_dict, doit_loader.Task):
                    tasks[task_dict.name] = task_dict
                else:
                    self._generate_task_from_yield(tasks, func_name, task_dict, x_doc)

            if tasks:
                return list(tasks.values())
            else:
                # special case task_generator did not generate any task
                # create an empty group task
                return [doit_loader.Task(func_name, None, doc=gen_doc, has_subtask=True)]

        if gen_result is None:
            return ()

        raise doit_loader.InvalidTask(
            "doit_loader.Task '%s'. Must return a dictionary or generator. Got %s" %
            (func_name, type(gen_result)))

    def _append_params(self, tasks, param_def):
        """Apply parameters defined for the task generator to the tasks

        defined by the generator.
        """
        for task in tasks:
            if task.subtask_of is None:  # only parent tasks
                # task.params can not be used with creator_params
                if task.params:
                    msg = (f"doit_loader.Task '{task.name}'. `params` attribute can not be used"
                        " in conjuction with `@self.task_params`")
                    raise InvalidTask(msg)
                task.creator_params = param_def

    def _process_gen(self, ref, creator_kwargs):
        """process a task creator, generating tasks"""
        gen_tasks = self._generate_tasks(self.current_name, ref(**creator_kwargs), ref.__doc__)
        if hasattr(ref, '_task_creator_params'):
            self._append_params(gen_tasks, ref._task_creator_params)
        self.task_list.extend(gen_tasks)

    def _add_delayed(self, tname, ref, original_delayed, kwargs):
        # Make sure create_after can be used on class methods.
        # delayed.creator is initially set by the decorator,
        # so always an unbound function.
        # Here we re-assign with the reference taken on doit load phase
        # because it is bounded method.
        this_delayed = copy.copy(delayed)
        this_delayed.creator = ref
        d_task = doit_loader.Task(tname, None, loader=this_delayed, doc=delayed.creator.__doc__)

        if hasattr(ref, '_task_creator_params'):
            this_delayed.kwargs = kwargs
            d_task.creator_params = getattr(ref, '_task_creator_params', None)
        self.task_list.append(d_task)
