#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import inspect
import logging as logmod
import pathlib as pl
import sys
from collections import OrderedDict
from copy import copy, deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from types import FunctionType, GeneratorType, MethodType
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import time
import doot
from doot.control.group import TaskGroup
from doot.control.locations import DootLocData
from doot.control.tasker import DootTasker
from doot.task.task import DootTask
from doot.utils.check_dirs import CheckDir
from doot.utils.gen_toml import GenToml
from doot.utils.task_namer import task_namer

TASK_STRING = "task_"

##-- loader cli params
#### options related to dooter.py
# select dodo file containing tasks
opt_doot = {
    "section" : "task loader",
    "name"    : "dooter",
    "short"   : "f",
    "long"    : "file",
    "type"    : str,
    "default" : str(doot.default_dooter),
    "env_var" : "DOOT_FILE",
    "help"    : "load task from doot FILE [default: %(default)s]"
}

opt_break = {
    "section" : "task loader",
    "name"    : "break",
    "short"   : "b",
    "long"    : "break",
    "type"    : bool,
    "default" : False,
    "help"    : "Start a debugger before loading tasks, to set breakpoints"
    }

# cwd
opt_cwd = {
    'section': 'task loader',
    'name': 'cwdPath',
    'short': 'd',
    'long': 'dir',
    'type': str,
    'default': None,
    'help': ("set path to be used as cwd directory "
             "(file paths on dodo file are relative to dodo.py location).")
}

# seek dodo file on parent folders
opt_seek_file = {
    'section': 'task loader',
    'name': 'seek_file',
    'short': 'k',
    'long': 'seek-file',
    'type': bool,
    'default': False,
    'env_var': 'DOIT_SEEK_FILE',
    'help': ("seek dodo file on parent folders [default: %(default)s]")
}

##-- end loader cli params

class DootLoader(TaskLoader_i):
    """
    Customized doit_loader.Task loader that automatically
    retrieves directory checks, and stores all created tasks
    for later retrieval
    """

    cmd_options : ClassVar[tuple]    = (opt_doot, opt_cwd, opt_seek_file, opt_break)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._task_collection = {}
        self._build_failures  = []
        self._task_class      = DootTaskExt

    def setup(self, opt_values):
        # lazily load namespace from dooter file per config parameters:
        if opt_values['break']:
            breakpoint()
            pass
        try:
            self.namespace = dict(inspect.getmembers(doit_loader.get_module(
                opt_values['dooter'],
                opt_values['cwdPath'],
                opt_values['seek_file'],
            )))
            self.namespace['__doot_all_dirs']   = DootLocData.as_taskgroup()
            self.namespace['__doot_all_checks'] = CheckDir.as_taskgroup()
            # self.namespace['__doot_all_tomls']  = GenToml.gen_toml_tasks()
        except doot.errors.DootDirAbsent as err:
            logging.error("LOCATION MISSING: %s", err.args[0])
            sys.exit(1)

    def load_config(self):
        self.config = doot.config.get_table()
        return self.config

    def load_tasks(self, cmd, pos_args) -> list:
        start_time = time.perf_counter()
        logging.debug("---- Loading Tasks")
        creators = self._get_task_creators(self.namespace, self.cmd_names)

        self._build_task_dict(creators, allow_delayed=cmd.execute_tasks, args=pos_args)
        self._add_task_options_from_config()
        self._add_task_options_from_api()

        logging.debug("Task List Size: %s", len(self._task_collection))
        logging.debug("Task List Names: %s", list(self._task_collection.keys()))
        if bool(self._build_failures):
            logging.warning("%s task build failures", len(self._build_failures))
        logging.debug("---- Tasks Loaded in %s seconds", f"{time.perf_counter() - start_time:0.4f}")


        return self._task_collection.values()

    def _get_task_creators(self, namespace, command_names):
        """
        get task creators defined in the namespace

        A task-creator is a function that:
        - task_name starts with the string TASK_STRING
        - has the attribute `create_doit_tasks`
        - is a DootTasker

        @return (list - func) task-creators
        """
        logging.debug("Getting Task Creators from namespace")
        creators : list[tuple[str,Any]] = []
        prefix_len : int                = len(TASK_STRING)

        for task_name, ref in namespace.items():
            match task_name.startswith(TASK_STRING), ref:
                case _, _ if task_name in command_names:
                    logging.warning("doot_loader.Task can't be called '%s' because this is a command task_name.", task_name)
                    continue
                case _, doit_loader.task_params:
                    # Do not solicit tasks from the @self.task_params decorator.
                    continue
                case _, TaskGroup() if bool(ref):
                    logging.debug("Expanding TaskGroup: %s", ref)
                    creators += [(getattr(x, "basename", task_name), x) for x in ref.tasks]
                case _,  DootTasker():
                    creators += [(ref.basename, ref)]
                case True, dict():
                    logging.info("Got a basic task dict: %s", task_name)
                    creators.append((task_name, ref))
                case True, FunctionType() | MethodType():
                    # function is a task creator because of its task_name
                    # remove TASK_STRING prefix from task_name
                    creators.append((task_name[prefix_len:], ref))
                case _, _ if getattr(ref, 'create_doit_tasks', False):
                    # object is a task creator because it contains the special method
                    # create_doit_tasks might have a basename to overwrite task task_name.
                    ref       = ref.create_doit_tasks
                    task_name = getattr(ref, 'basename', task_name)
                    creators.append((task_name, ref))
                case _, _:
                    continue

        return creators

    def _build_task_dict(self, creators, allow_delayed=False, args=()):
        """
        Run each task creator, or delay it
        """
        for name, ref in creators:
            # Parse command line arguments for task generator parameters
            param_spec, creator_kwargs = self._parse_creator_params(name, ref, args)
            delayed        = getattr(ref, "_build_delayed", None) or getattr(ref, 'doit_create_after', None)

            match delayed:
                case True if allow_delayed:
                    delay_obj = DelayedLoader(None)
                    self._build_delayed(name, ref, delay_obj, creator_kwargs)
                    continue
                case FunctionType() | MethodType():
                    delay_name = getattr(ref, "delayed_subtask_name", task_namer(ref.basename, "delayed", private=True))
                    self._build_delayed(delay_name, delayed, DelayedLoader(None))
                case DelayedLoader() if bool(delayed.creates):
                    for tname in delayed.creates:
                        self._build_delayed(tname, ref, delayed, creator_kwargs)
                case DelayedLoader():
                    self._build_delayed(name, ref, delayed, creator_kwargs)
                case None:
                    pass

            self._generate_tasks(name, ref, creator_kwargs, param_spec)

    def _build_delayed(self, tname, delay_fn, original_delayed):
        # Here we re-assign with the reference taken on doit load phase
        # because it is bounded method.
        logging.debug("Delaying: %s", tname)
        this_delayed = copy(original_delayed)
        this_delayed.creator = delay_fn
        d_task = self._task_class(tname, None, loader=this_delayed, doc=original_delayed.creator.__doc__)
        self._add_task(d_task)

    def _add_task(self, task, param_spec=None):
        if task is None:
            return

        if task.subtask_of is not None:
            match self._task_collection.get(task.subtask_of, None):
                case None:
                    logging.warning("No Group Task found for Sub Task: %s", task.name)
                    self._build_failures.append(task)
                    return
                case group_task:
                    group_task.task_dep.append(task.name)

        if self._task_collection.get(task.name, False):
            logging.warning("Duplicate Task Name Specified: %s", task.name)
            self._build_failures.append(task)
            return

        if not task.subtask_of and bool(param_spec):
            logging.debug("Adding params spec to task: %s : %s", task.name, param_spec)
            task.creator_params = param_spec

        self._task_collection[task.name] = task

    def _generate_tasks(self, func_name, gen_result, creator_kwargs, param_spec, gen_doc=None) -> list:
        new_task = None
        match gen_result:
            case doit_loader.Task():
                # a task instance, just return it without any processing
                logging.debug("Task is a Task Object, nothing to do: %s", gen_result.name)
                new_task = gen_result
            case DootTasker():
                self._generate_tasks(func_name, gen_result.build(**creator_kwargs), creator_kwargs, param_spec, gen_doc)
            case FunctionType() | MethodType():
                self._generate_tasks(func_name, gen_result(**creator_kwargs), param_spec, gen_doc)
            case {"head_task" : _ }:
                new_task = self._generate_solo_task(func_name, gen_result, gen_doc)
            case { "basename": base, "name" : _ }:
                if gen_result['basename'] not in self._task_collection:
                    leader_task = self._generate_solo_task(base, {"actions": [], "head_task": True}, gen_doc)
                    self._add_task(leader_task, param_spec)
                new_task = self._generate_sub_task(func_name, gen_result, gen_doc)
            case dict():
                new_task = self._generate_solo_task(func_name, gen_result, gen_doc)
            case GeneratorType():
                logging.debug("%s : Task is a generator, running", func_name)
                for sub_result in gen_result:
                    self._generate_tasks(func_name, sub_result, creator_kwargs, param_spec, gen_doc=gen_doc)
                logging.debug("%s : Generator Finished", func_name)
            case [*maybe_tasks]:
                for sub_task in maybe_tasks:
                    self._generate_tasks(func_name, sub_task, creator_kwargs, param_spec, gen_doc=gen_doc)
            case None:
                pass
            case _:
                logging.warning("Unrecognized Task creator result: %s", gen_result)
                self._build_failures.append(gen_result)

        self._add_task(new_task, param_spec)

    def _generate_solo_task(self, func_name, task_dict, gen_doc):
        """generate a single task from a dict returned by a task generator"""
        logging.debug("Generator %s Returned a Value, building task from it", func_name)
        private = task_dict.get("private", False)
        task_dict['name'] = task_namer(task_dict.pop('basename', func_name), private=private)
        # Use task generator docstring
        # if no doc present in task dict
        if 'doc' not in task_dict:
            task_dict['doc'] = gen_doc

        task = self._task_class(**task_dict)
        if task_dict.get("head_task", False):
            task.has_subtask = True

        return task

    def _generate_sub_task(self, func_name, task_dict, gen_doc):
        """generate a single task from a dict yielded by task generator

        @param tasks: dictionary with created tasks
        @return None: the created task is added to 'tasks' dict
        """
        logging.debug("Generator %s yielded value, building task from it", func_name)
        basename          = task_dict.pop('basename', None) or func_name
        private           = task_dict.get("private", True)
        task_dict['name'] = task_namer(basename, task_dict.get('name', ""), private=private)
        if 'doc' not in task_dict:
            task_dict['doc'] = gen_doc

        sub_task            = self._task_class(**task_dict)
        sub_task.subtask_of = task_namer(basename)
        return sub_task

    def _parse_creator_params(self, name, ref, args) -> (list, dict):
        logging.debug("Parsing Creator Params for: %s", name)
        arg_pos        = {}
        creator_params = None
        parser         = None
        task_stanza    = 'task:' + name

        # Map arg_name to its position.
        # Save only args that do not start with `-` (potentially task names)
        for index, term in enumerate(args):
            if term[0] != '-':
                arg_pos[term] = index

        if hasattr(ref, 'set_params'):
            creator_params = ref.set_params()
            ref._task_creator_params = creator_params
        else:
            creator_params = getattr(ref, '_task_creator_params', None)

        if creator_params is None:
            return [], {}

        logging.debug("Creator has params: %s", creator_params)
        # Add task options from config, if present
        parser      = doit_loader.TaskParse([doit_loader.CmdOption(opt) for opt in creator_params])
        if self.config and task_stanza in self.config:
            parser.overwrite_defaults(self.config[task_stanza])

        # parse params from doit api or cli args
        if self.task_opts is not None and name in self.task_opts: # pylint: disable=unsupported-membership-test
            creator_kwargs = self.task_opts[name] # pylint: disable=unsubscriptable-object
        elif name in arg_pos:
            creator_kwargs, _ = parser.parse(args[arg_pos[name] + 1:])
        else:
            creator_kwargs, _ = parser.parse('')

        return creator_params, creator_kwargs

    def _add_task_options_from_config(self):
        # Add task options from config, if present
        if self.config is None:
            return

        for task in self._task_collection.values():
            task_stanza = "task:" + task.name
            if task_stanza in self.config:
                task.cfg_values = self.config[task_stanza]

    def _add_task_options_from_api(self):
        # add values from API run_tasks() usage
        if self.task_opts is None:
            return

        for task in self._task_collection:
            if task.name in self.task_opts: # pylint: disable=unsupported-membership-test
                task.cfg_values = self.task_opts[task.name] # pylint: disable=unsubscriptable-object
                if task.pos_arg and task.pos_arg in task.cfg_values:
                    task.pos_arg_val = task.cfg_values[task.pos_arg]
