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

class ExecutionResult(enum.Enum):
    # execution result.
    SUCCESS = enum.auto()
    FAILURE = enum.auto()
    ERROR   = enum.auto()

class TaskStatus_i:
    """Result object for Dependency.get_status.

    @ivar status: (str) one of "run", "up-to-date" or "error"
    """

    def __init__(self, get_log):
        self.get_log = get_log
        self.status = 'up-to-date'
        # save reason task is not up-to-date
        self.reasons = defaultdict(list)
        self.error_reason = None

    def add_reason(self, reason, arg, status='run'):
        """sets state and append reason for not being up-to-date
        :return boolean: processing should be interrupted
        """
        self.status = status
        if self.get_log:
            self.reasons[reason].append(arg)
        return not self.get_log

    def set_reason(self, reason, arg):
        """sets state and reason for not being up-to-date
        :return boolean: processing should be interrupted
        """
        self.status = 'run'
        if self.get_log:
            self.reasons[reason] = arg
        return not self.get_log

    def get_error_message(self):
        '''return str with error message'''
        return self.error_reason

class TaskDependency_i:
    """Manage tasks dependencies.

    Each dependency is saved in "db". There are several "db" backends.
    It uses a Key-Value format where the key is task-name
    and value is a dictionary.
    Each task has a dictionary where keys are `dependency`'s (absolute file path),
    and the value is the dependency signature.
    Apart from dependencies other values are also saved on the task dictionary:

    * ``_values_:`` task's values
    * ``result:`` task result

    And also some internal doot attributes:

    * ``ignore:``
    * ``deps:``
    * ``checker:``

    Those can be accessed with generic DB ``get()``, see below...

    :ivar string name: filepath of the DB file
    :ivar bool _closed: DB was flushed to file
    """

    def __init__(self, db_class, backend_name, checker_cls=MD5Checker,
                 codec_cls=JSONCodec, module_name=None):
        self._closed = False
        self.checker = checker_cls()
        self.db_class = db_class
        self.backend = db_class(backend_name, codec=codec_cls(), module_name=module_name)
        self._set = self.backend.set
        self._get = self.backend.get
        self.remove = self.backend.remove
        self.remove_all = self.backend.remove_all
        self._in = self.backend.in_
        self.name = self.backend.name

    def close(self):
        """Write DB in file"""
        if not self._closed:
            self.backend.dump()
            self._closed = True

    ####### task specific

    def save_success(self, task, result_hash=None):
        """save info after a task is successfully executed

        :param str result_hash: explicitly set result_hash
        """
        # save task values
        self._set(task.name, "_values_:", task.values)

        # save task result md5
        if result_hash is not None:
            self._set(task.name, "result:", result_hash)
        elif task.result:
            if isinstance(task.result, dict):
                self._set(task.name, "result:", task.result)
            else:
                self._set(task.name, "result:", get_md5(task.result))

        # file-dep
        self._set(task.name, 'checker:', self.checker.__class__.__name__)
        for dep in task.file_dep:
            state = self.checker.get_state(dep, self._get(task.name, dep))
            if state is not None:
                self._set(task.name, dep, state)

        # save list of file_deps
        self._set(task.name, 'deps:', tuple(task.file_dep))

    def get_values(self, task_name):
        """get all saved values from a task

        :return dict:
        """
        values = self._get(task_name, '_values_:')
        return values or {}

    def get_value(self, task_id, key_name):
        """get saved value from task

        :param str task_id:
        :param str key_name: key result dict of the value
        """
        if not self._in(task_id):
            # FIXME do not use generic exception
            raise Exception("taskid '%s' has no computed value!" % task_id)
        values = self.get_values(task_id)
        if key_name not in values:
            msg = "Invalid arg name. Task '%s' has no value for '%s'."
            raise Exception(msg % (task_id, key_name))
        return values[key_name]

    def get_result(self, task_name):
        """get the result saved from a task

        :return (dict or md5sum):
        """
        return self._get(task_name, 'result:')

    def remove_success(self, task):
        """remove saved info from task"""
        self.remove(task.name)

    def ignore(self, task):
        """mark task to be ignored"""
        self._set(task.name, 'ignore:', '1')

    def status_is_ignore(self, task):
        """check if task is marked to be ignored"""
        return self._get(task.name, "ignore:")

    def get_status(self, task, tasks_dict, get_log=False):
        """Check if task is up to date. set task.dep_changed

        If the checker class changed since the previous run, the task is
        deleted, to be sure that its state is not re-used.

        @param task: (Task)
        @param tasks_dict: (dict: Task) passed to objects used on uptodate
        @param get_log: (bool) if True, adds all reasons to the return
                               object why this file will be rebuild.
        @return: (DependencyStatus) a status object with possible status
                                    values up-to-date, run or error

        task.dep_changed (list-strings): file-dependencies that are not
        up-to-date if task not up-to-date because of a target, returned value
        will contain all file-dependencies regardless they are up-to-date
        or not.
        """
        result = DependencyStatus(get_log)
        task.dep_changed = []

        # check uptodate bool/callables
        uptodate_result_list = []
        for utd, utd_args, utd_kwargs in task.uptodate:
            # if parameter is a callable
            if hasattr(utd, '__call__'):
                # FIXME control verbosity, check error messages
                # 1) setup object with global info all tasks
                if isinstance(utd, UptodateCalculator):
                    utd.setup(self, tasks_dict)
                # 2) add magic positional args for `task` and `values`
                # if present.
                spec_args = list(inspect.signature(utd).parameters.keys())
                magic_args = []
                for i, name in enumerate(spec_args):
                    if i == 0 and name == 'task':
                        magic_args.append(task)
                    elif i == 1 and name == 'values':
                        magic_args.append(self.get_values(task.name))
                args = magic_args + utd_args
                # 3) call it and get result
                uptodate_result = utd(*args, **utd_kwargs)
            elif isinstance(utd, str):
                uptodate_result = subprocess.call(
                    utd, shell=True,
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL) == 0
            # parameter is a value
            else:
                uptodate_result = utd

            # None means uptodate was not really calculated and should be
            # just ignored
            if uptodate_result is None:
                continue
            uptodate_result_list.append(uptodate_result)
            if not uptodate_result:
                result.add_reason('uptodate_false', (utd, utd_args, utd_kwargs))

        # any uptodate check is false
        if not get_log and result.status == 'run':
            return result

        # no dependencies means it is never up to date.
        if not (task.file_dep or uptodate_result_list):
            if result.set_reason('has_no_dependencies', True):
                return result

        # if target file is not there, task is not up to date
        for targ in task.targets:
            if not self.checker.exists(targ):
                task.dep_changed = list(task.file_dep)
                if result.add_reason('missing_target', targ):
                    return result

        # check for modified file_dep checker
        previous = self._get(task.name, 'checker:')
        checker_name = self.checker.__class__.__name__
        if previous and previous != checker_name:
            task.dep_changed = list(task.file_dep)
            # remove all saved values otherwise they might be re-used by
            # some optimization on MD5Checker.get_state()
            self.remove(task.name)
            if result.set_reason('checker_changed', (previous, checker_name)):
                return result

        # check for modified file_dep
        previous = self._get(task.name, 'deps:')
        previous_set = set(previous) if previous else None
        if previous_set and previous_set != task.file_dep:
            if get_log:
                added_files = sorted(list(task.file_dep - previous_set))
                removed_files = sorted(list(previous_set - task.file_dep))
                result.set_reason('added_file_dep', added_files)
                result.set_reason('removed_file_dep', removed_files)
            result.status = 'run'

        # list of file_dep that changed
        check_modified = self.checker.check_modified
        changed = []
        for dep in task.file_dep:
            state = self._get(task.name, dep)
            try:
                file_stat = self.checker.info(dep)
            except self.checker.CheckerError:
                error_msg = "Dependent file '{}' does not exist.".format(dep)
                result.error_reason = error_msg.format(dep)
                if result.add_reason('missing_file_dep', dep, 'error'):
                    return result
            else:
                if state is None or check_modified(dep, file_stat, state):
                    changed.append(dep)
        task.dep_changed = changed

        if len(changed) > 0:
            result.set_reason('changed_file_dep', changed)

        return result



class TaskHandler_i:
    """Manages tasks inter-relationship

    There are 3 phases
      1) the constructor gets a list of tasks and do initialization
      2) 'process' the command line options for tasks are processed
      3) 'task_dispatcher' dispatch tasks to runner

    Process dependencies and targets to find out the order tasks
    should be executed. Also apply filter to exclude tasks from
    execution. And parse task cmd line options.

    @ivar tasks: (dict) Key: task name ([taskgen.]name)
                               Value: L{Task} instance
    @ivar targets: (dict) Key: fileName
                          Value: task_name
    """

    def __init__(self, task_list, auto_delayed_regex=False):
        self.tasks = OrderedDict()
        self.targets = {}
        self.auto_delayed_regex = auto_delayed_regex

        # name of task in order to be executed
        # this the order as in the dodo file. the real execution
        # order might be different if the dependencies require so.
        self._def_order = []
        # list of tasks selected to be executed
        self.selected_tasks = None

        # sanity check and create tasks dict
        for task in task_list:
            # task must be a Task
            if not isinstance(task, Task):
                msg = "Task must be an instance of Task class. %s"
                raise InvalidTask(msg % (task.__class__))
            # task name must be unique
            if task.name in self.tasks:
                msg = "Task names must be unique. %s"
                raise InvalidDodoFile(msg % task.name)

            self.tasks[task.name] = task
            self._def_order.append(task.name)

        # expand wild-card task-dependencies
        for task in self.tasks.values():
            for pattern in task.wild_dep:
                task.task_dep.extend(self._get_wild_tasks(pattern))

        self._check_dep_names()
        self.set_implicit_deps(self.targets, task_list)


    def _check_dep_names(self):
        """check if user input task_dep or setup_task that doesnt exist"""
        # check task-dependencies exist.
        for task in self.tasks.values():
            for dep in task.task_dep:
                if dep not in self.tasks:
                    msg = f"{task.name}. Task dependency '{dep}' does not exist."
                    raise InvalidTask(msg)

            for setup_task in task.setup_tasks:
                if setup_task not in self.tasks:
                    msg = f"Task '{task.name}': invalid setup task '{setup_task}'."
                    raise InvalidTask(msg)


    @staticmethod
    def set_implicit_deps(targets, task_list):
        """set/add task_dep based on file_dep on a target from another task
        @param targets: (dict) fileName -> task_name
        @param task_list: (list - Task) task with newly added file_dep
        """
        # 1) create a dictionary associating every target->task. where the task
        # builds that target.
        for task in task_list:
            for target in task.targets:
                if target in targets:
                    msg = ("Two different tasks can't have a common target."
                           "'%s' is a target for %s and %s.")
                    raise InvalidTask(msg % (target, task.name, targets[target]))
                targets[target] = task.name

        # 2) now go through all dependencies and check if they are target from
        # another task.
        # Note: When used with delayed tasks.
        #       It does NOT check if a delayed-task's target is a file_dep
        #       from another previously created task.
        for task in task_list:
            TaskControl.add_implicit_task_dep(targets, task, task.file_dep)


    @staticmethod
    def add_implicit_task_dep(targets, task, deps_list):
        """add implicit task_dep for `task` for newly added `file_dep`

        @param targets: (dict) fileName -> task_name
        @param task: (Task) task with newly added file_dep
        @param dep_list: (list - str): list of file_dep for task
        """
        for dep in deps_list:
            if (dep in targets and targets[dep] not in task.task_dep):
                task.task_dep.append(targets[dep])


    def _get_wild_tasks(self, pattern):
        """get list of tasks that match pattern"""
        wild_list = []
        for t_name in self._def_order:
            if fnmatch.fnmatch(t_name, pattern):
                wild_list.append(t_name)
        return wild_list


    def _process_filter(self, task_selection):
        """process cmd line task options
        [task_name [-task_opt [opt_value]] ...] ...

        @param task_selection: list of strings with task names/params or target
        @return list of task names. Expanding glob and removed params
        """
        filter_list = []
        def add_filtered_task(seq, f_name):
            """add task to list `filter_list` and set task.options from params
            @return list - str: of elements not yet
            """
            filter_list.append(f_name)
            # only tasks specified by name can contain parameters
            if f_name in self.tasks:
                # parse task_selection
                the_task = self.tasks[f_name]

                # Initialize options for the task
                seq = the_task.init_options(seq)

                # if task takes positional parameters set all as pos_arg_val
                if the_task.pos_arg is not None:
                    # cehck value is not set yet
                    # it could be set directly with api.run_tasks()
                    #     -> NamespaceTaskLoader.load_tasks()
                    if the_task.pos_arg_val is None:
                        the_task.pos_arg_val = seq
                        seq = []
            return seq

        # process...
        seq = task_selection[:]
        # process cmd_opts until nothing left
        while seq:
            f_name = seq.pop(0)  # always start with a task/target name
            # select tasks by task-name pattern
            if '*' in f_name:
                for task_name in self._get_wild_tasks(f_name):
                    add_filtered_task((), task_name)
            else:
                seq = add_filtered_task(seq, f_name)
        return filter_list


    def _filter_tasks(self, task_selection):
        """Select tasks specified by filter.

        @param task_selection: list of strings with task names/params or target
        @return (list) of string. where elements are task name.
        """
        selected_task = []

        filter_list = self._process_filter(task_selection)
        for filter_ in filter_list:
            # by task name
            if filter_ in self.tasks:
                selected_task.append(filter_)
                continue

            # by target
            if filter_ in self.targets:
                selected_task.append(self.targets[filter_])
                continue

            # if can not find name check if it is a sub-task of a delayed
            basename = filter_.split(':', 1)[0]
            if basename in self.tasks:
                loader = self.tasks[basename].loader
                if not loader:
                    raise InvalidCommand(not_found=filter_)
                loader.basename = basename
                self.tasks[filter_] = Task(filter_, None, loader=loader)
                selected_task.append(filter_)
                continue

            # check if target matches any regex
            delayed_matched = []  # list of Task
            for task in list(self.tasks.values()):
                if not task.loader:
                    continue
                if task.name.startswith('_regex_target'):
                    continue
                if task.loader.target_regex:
                    if re.match(task.loader.target_regex, filter_):
                        delayed_matched.append(task)
                elif self.auto_delayed_regex:
                    delayed_matched.append(task)
            delayed_matched_names = [t.name for t in delayed_matched]
            regex_group = _RegexGroup(filter_, set(delayed_matched_names))

            # create extra tasks to load delayed tasks matched by regex
            for task in delayed_matched:
                loader = task.loader
                loader.basename = task.name
                name = '{}_{}:{}'.format('_regex_target', filter_, task.name)
                loader.regex_groups[name] = regex_group
                self.tasks[name] = Task(name, None,
                                        loader=loader,
                                        file_dep=[filter_])
                selected_task.append(name)

            if not delayed_matched:
                # not found
                raise InvalidCommand(not_found=filter_)
        return selected_task


    def process(self, task_selection):
        """
        @param task_selection: list of strings with task names/params
        @return (list - string) each element is the name of a task
        """
        # execute only tasks in the filter in the order specified by filter
        if task_selection is not None:
            self.selected_tasks = self._filter_tasks(task_selection)
        else:
            # if no filter is defined execute all tasks
            # in the order they were defined.
            self.selected_tasks = self._def_order


    def task_dispatcher(self):
        """return a TaskDispatcher generator
        """
        assert self.selected_tasks is not None, \
            "must call 'process' before this"

        return TaskDispatcher(self.tasks, self.targets, self.selected_tasks)


class TaskManager_i:
    """Dispatch another task to be selected/executed, mostly handle with MP

    Note that a dispatched task might not be ready to be executed.
    """

    def __init__(self, tasks, targets, selected_tasks):
        self.tasks = tasks
        self.targets = targets
        self.selected_tasks = selected_tasks

        self.nodes = {}  # key task-name, value: _ExecNode
        # queues
        self.waiting = set()  # of _ExecNode
        self.ready = deque()  # of _ExecNode

        self.generator = self._dispatcher_generator(selected_tasks)

    def _gen_node(self, parent, task_name):
        """return _ExecNode for task_name if not created yet"""
        node = self.nodes.get(task_name, None)

        # first time, create node
        if node is None:
            node = _ExecNode(self.tasks[task_name], parent)
            node.generator = self._add_task(node)
            self.nodes[task_name] = node
            return node

        # detect cyclic/recursive dependencies
        if parent and task_name in parent.ancestors:
            msg = "Cyclic/recursive dependencies for task %s: [%s]"
            cycle = " -> ".join(parent.ancestors + [task_name])
            raise InvalidDodoFile(msg % (task_name, cycle))

    def _node_add_wait_run(self, node, task_list, calc=False):
        """updates node.wait_run
        @param node (_ExecNode)
        @param task_list (list - str) tasks that node should wait for
        @param calc (bool) task_list is for calc_dep
        """
        # wait_for: contains tasks that `node` needs to wait for and
        # were not executed yet.
        wait_for = set()
        for name in task_list:
            dep_node = self.nodes[name]
            if (not dep_node) or dep_node.run_status in (None, 'run'):
                wait_for.add(name)
            else:
                # if dep task was already executed:
                # a) set parent status
                node.parent_status(dep_node)
                # b) update dependencies from calc_dep results
                if calc:
                    self._process_calc_dep_results(dep_node, node)

        # update _ExecNode setting parent/dependent relationship
        for name in wait_for:
            self.nodes[name].waiting_me.add(node)
        if calc:
            node.wait_run_calc.update(wait_for)
        else:
            node.wait_run.update(wait_for)

    @no_none
    def _add_task(self, node):
        """@return a generator that produces:
             - _ExecNode for task dependencies
             - 'wait' to wait for an event (i.e. a dep task run)
             - Task when ready to be dispatched to runner (run or be selected)
             - None values are of no interest and are filtered out
               by the decorator no_none

        note that after a 'wait' is sent it is the responsibility of the
        caller to ensure the current _ExecNode cleared all its waiting
        before calling `next()` again on this generator
        """
        this_task = node.task

        # skip this task if task belongs to a regex_group that already
        # executed the task used to build the given target
        if this_task.loader:
            regex_group = this_task.loader.regex_groups.get(this_task.name, None)
            if regex_group and regex_group.found:
                return

        # add calc_dep & task_dep until all processed
        # calc_dep may add more deps so need to loop until nothing left
        while True:
            calc_dep_list = list(node.calc_dep)
            node.calc_dep.clear()
            task_dep_list = node.task_dep[:]
            node.task_dep = []

            for calc_dep in calc_dep_list:
                yield self._gen_node(node, calc_dep)
            self._node_add_wait_run(node, calc_dep_list, calc=True)

            # add task_dep
            for task_dep in task_dep_list:
                yield self._gen_node(node, task_dep)
            self._node_add_wait_run(node, task_dep_list)

            # do not wait until all possible task_dep are created
            if (node.calc_dep or node.task_dep):
                continue  # pragma: no cover  # coverage cant catch this #198
            elif (node.wait_run or node.wait_run_calc):
                yield 'wait'
            else:
                break

        # generate tasks from a DelayedLoader
        if this_task.loader:
            ref = this_task.loader.creator
            to_load = this_task.loader.basename or this_task.name
            this_loader = self.tasks[to_load].loader
            if this_loader and not this_loader.created:
                task_gen = ref(**this_loader.kwargs) if this_loader.kwargs else ref()
                new_tasks = generate_tasks(to_load, task_gen, ref.__doc__)
                TaskControl.set_implicit_deps(self.targets, new_tasks)
                for nt in new_tasks:
                    if not nt.loader:
                        nt.loader = DelayedLoaded
                    self.tasks[nt.name] = nt
            # check itself for implicit dep (used by regex_target)
            TaskControl.add_implicit_task_dep(
                self.targets, this_task, this_task.file_dep)

            # remove file_dep since generated tasks are not required
            # to really create the target (support multiple matches)
            if regex_group:
                this_task.file_dep = {}
                if regex_group.target in self.targets:
                    regex_group.found = True
                else:
                    regex_group.tasks.remove(this_task.loader.basename)
                    if len(regex_group.tasks) == 0:
                        # In case no task is left, we cannot find a task
                        # generating this target. Print an error message!
                        raise InvalidCommand(not_found=regex_group.target)

            # mark this loader to not be executed again
            this_task.loader.created = True
            this_task.loader = DelayedLoaded

            # this task was placeholder to execute the loader
            # now it needs to be re-processed with the real task
            yield "reset generator"
            assert False, "This generator can not be used again"

        # add itself
        yield this_task

        # tasks that contain setup-tasks need to be yielded twice
        if this_task.setup_tasks:
            # run_status None means task is waiting for other tasks
            # in order to check if up-to-date. so it needs to wait
            # before scheduling its setup-tasks.
            if node.run_status is None:
                node.wait_select = True
                yield "wait"

            # if this task should run, so schedule setup-tasks before itself
            if node.run_status == 'run':
                for setup_task in this_task.setup_tasks:
                    yield self._gen_node(node, setup_task)
                self._node_add_wait_run(node, this_task.setup_tasks)
                if node.wait_run:
                    yield 'wait'

                # re-send this task after setup_tasks are sent
                yield this_task

    def _get_next_node(self, ready, tasks_to_run):
        """get _ExecNode from (in order):
            .1 ready
            .2 tasks_to_run (list in reverse order)
         """
        if ready:
            return ready.popleft()
        # get task group from tasks_to_run
        while tasks_to_run:
            task_name = tasks_to_run.pop()
            node = self._gen_node(None, task_name)
            if node:
                return node

    def _update_waiting(self, processed):
        """updates 'ready' and 'waiting' queues after processed
        @param processed (_ExecNode) or None
        """
        # no task processed, just ignore
        if processed is None:
            return

        node = processed

        # if node was waiting select must only receive select event
        if node.wait_select:
            self.ready.append(node)
            self.waiting.remove(node)
            node.wait_select = False

        # status == run means this was not just select completed
        if node.run_status == 'run':
            return

        for waiting_node in node.waiting_me:
            waiting_node.parent_status(node)

            # is_ready indicates if node.generator can be invoked again
            task_name = node.task.name

            # node wait_run will be ready if there are nothing left to wait
            if task_name in waiting_node.wait_run:
                waiting_node.wait_run.remove(task_name)
                is_ready = not (waiting_node.wait_run or waiting_node.wait_run_calc)
            # node wait_run_calc
            else:
                assert task_name in waiting_node.wait_run_calc
                waiting_node.wait_run_calc.remove(task_name)
                # calc_dep might add new deps that can be run without
                # waiting for the completion of the remaining deps
                is_ready = True
                self._process_calc_dep_results(node, waiting_node)

            # this node can be further processed
            if is_ready and (waiting_node in self.waiting):
                self.ready.append(waiting_node)
                self.waiting.remove(waiting_node)

    def _process_calc_dep_results(self, node, waiting_node):
        # refresh this task dependencies with values got from calc_dep
        values = node.task.values
        len_task_deps = len(waiting_node.task.task_dep)
        old_calc_dep = waiting_node.task.calc_dep.copy()
        waiting_node.task.update_deps(values)
        TaskControl.add_implicit_task_dep(
            self.targets, waiting_node.task,
            values.get('file_dep', []))

        # update node's list of non-processed dependencies
        new_task_dep = waiting_node.task.task_dep[len_task_deps:]
        waiting_node.task_dep.extend(new_task_dep)
        new_calc_dep = waiting_node.task.calc_dep - old_calc_dep
        waiting_node.calc_dep.update(new_calc_dep)

    def _dispatcher_generator(self, selected_tasks):
        """return generator dispatching tasks"""
        # each selected task will create a tree (from dependencies) of
        # tasks to be processed
        tasks_to_run = list(reversed(selected_tasks))
        node = None  # current active _ExecNode

        while True:
            # get current node
            if not node:
                node = self._get_next_node(self.ready, tasks_to_run)
                if not node:
                    if self.waiting:
                        # all tasks are waiting, hold on
                        processed = (yield "hold on")
                        self._update_waiting(processed)
                        continue
                    # we are done!
                    return

            # get next step from current node
            next_step = node.step()

            # got None, nothing left for this generator
            if next_step is None:
                node = None
                continue

            # got a task, send _ExecNode to runner
            if isinstance(next_step, Task):
                processed = (yield self.nodes[next_step.name])
                self._update_waiting(processed)

            # got new _ExecNode, add to ready_queue
            elif isinstance(next_step, _ExecNode):
                self.ready.append(next_step)

            # node just performed a delayed creation of tasks, restart
            elif next_step == "reset generator":
                node.reset_task(self.tasks[node.task.name],
                                self._add_task(node))

            # got 'wait', add _ExecNode to waiting queue
            else:
                assert next_step == "wait"
                self.waiting.add(node)
                node = None

class TaskRunner_i:
    """Task runner

    run_tasks(X, Y...) ->
    calc_deps(X, Y...) -> Z
    manager.start(Z) ->
    loop: get_next -> A -> run(A) -> update_deps(A)
    """

    def __init__(self, dep_manager, reporter, continue_=False, always_execute=False, stream=None):
        """
        @param dep_manager: DependencyBase
        @param reporter: reporter object to be used
        @param continue_: (bool) execute all tasks even after a task failure
        @param always_execute: (bool) execute even if up-to-date or ignored
        @param stream: (task.Stream) global verbosity
        """
        self.dep_manager    = dep_manager
        self.reporter       = reporter
        self.continue_      = continue_
        self.always_execute = always_execute
        self.stream         = stream if stream else Stream(0)

        self.teardown_list = []  # list of tasks to be teardown
        self.final_result  = SUCCESS  # until something fails
        self._stop_running = False

    def select_task(self, node, tasks_dict):
        """Returns bool, task should be executed
         * side-effect: set task.options

        Tasks should be executed if they are not up-to-date.

        Tasks that contains setup-tasks must be selected twice,
        so it gives chance for dependency tasks to be executed after
        checking it is not up-to-date.
        """
        pass

    def execute_task(self, task):
        """execute task's actions"""
        pass

    def process_task_result(self, node, base_fail):
        """handles result"""
        pass

    def run_tasks(self, *tasks):
        """This will actually run/execute the tasks.
        It will check file dependencies to decide if task should be executed
        and save info on successful runs.
        It also deals with output to stdout/stderr.

        @param task_dispatcher: L{TaskDispacher}
        """
        pass

    def teardown(self):
        """run teardown from all tasks"""
        pass

    def finish(self):
        """finish running tasks"""
        pass
