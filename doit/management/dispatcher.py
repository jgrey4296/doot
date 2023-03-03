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


class TaskDispatcher:
    """Dispatch another task to be selected/executed, mostly handle with MP

    Note that a dispatched task might not be ready to be executed.
    """
    def __init__(self, tasks, targets, selected_tasks):
        self.tasks = tasks
        self.targets = targets
        self.selected_tasks = selected_tasks

        self.nodes = {}  # key task-name, value: ExecNode
        # queues
        self.waiting = set()  # of ExecNode
        self.ready = deque()  # of ExecNode

        self.generator = self._dispatcher_generator(selected_tasks)


    def _gen_node(self, parent, task_name):
        """return ExecNode for task_name if not created yet"""
        node = self.nodes.get(task_name, None)

        # first time, create node
        if node is None:
            node = ExecNode(self.tasks[task_name], parent)
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
        @param node (ExecNode)
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


        # update ExecNode setting parent/dependent relationship
        for name in wait_for:
            self.nodes[name].waiting_me.add(node)
        if calc:
            node.wait_run_calc.update(wait_for)
        else:
            node.wait_run.update(wait_for)


    @no_none
    def _add_task(self, node):
        """@return a generator that produces:
             - ExecNode for task dependencies
             - 'wait' to wait for an event (i.e. a dep task run)
             - Task when ready to be dispatched to runner (run or be selected)
             - None values are of no interest and are filtered out
               by the decorator no_none

        note that after a 'wait' is sent it is the responsibility of the
        caller to ensure the current ExecNode cleared all its waiting
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
        """get ExecNode from (in order):
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
        @param processed (ExecNode) or None
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
        node = None  # current active ExecNode

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

            # got a task, send ExecNode to runner
            if isinstance(next_step, Task):
                processed = (yield self.nodes[next_step.name])
                self._update_waiting(processed)

            # got new ExecNode, add to ready_queue
            elif isinstance(next_step, ExecNode):
                self.ready.append(next_step)

            # node just performed a delayed creation of tasks, restart
            elif next_step == "reset generator":
                node.reset_task(self.tasks[node.task.name],
                                self._add_task(node))

            # got 'wait', add ExecNode to waiting queue
            else:
                assert next_step == "wait"
                self.waiting.add(node)
                node = None
