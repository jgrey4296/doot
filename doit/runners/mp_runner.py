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

class MReporter:
    """send reported messages to master process

    puts a dictionary {'name': <task-name>,
                       'reporter': <reporter-method-name>}
    on runner's 'result_q'
    """
    def __init__(self, runner, reporter_cls):
        self.runner = runner
        self.reporter_cls = reporter_cls

    def __getattr__(self, method_name):
        """substitute any reporter method with a dispatching method"""
        if not hasattr(self.reporter_cls, method_name):
            raise AttributeError(method_name)
        def rep_method(task):
            self.runner.result_q.put({
                'name': task.name,
                'reporter': method_name,
            })
        return rep_method

    def complete_run(self):
        """ignore this on MReporter"""
        pass



class MRunner(Runner):
    """MultiProcessing Runner """
    Queue = staticmethod(MQueue)
    Child = staticmethod(Process)

    @staticmethod
    def available():
        """check if multiprocessing module is available"""
        # see: https://bitbucket.org/schettino72/doit/issue/17
        #      http://bugs.python.org/issue3770
        # not available on BSD systens
        try:
            import multiprocessing.synchronize
            multiprocessing  # pyflakes
        except ImportError:  # pragma: no cover
            return False
        else:
            return True

    def __init__(self, dep_manager, reporter,
                 continue_=False, always_execute=False,
                 stream=None, num_process=1):
        Runner.__init__(self, dep_manager, reporter, continue_=continue_,
                        always_execute=always_execute, stream=stream)
        self.num_process = num_process

        self.free_proc = 0   # number of free process
        self.task_dispatcher = None  # TaskDispatcher retrieve tasks
        self.tasks = None    # dict of task instances by name
        self.result_q = None


    def __getstate__(self):
        # multiprocessing on Windows will try to pickle self.
        # These attributes are actually not used by spawend process so
        # safe to be removed.
        pickle_dict = self.__dict__.copy()
        pickle_dict['reporter'] = None
        pickle_dict['task_dispatcher'] = None
        pickle_dict['dep_manager'] = None
        return pickle_dict

    def get_next_job(self, completed):
        """get next task to be dispatched to sub-process

        On MP needs to check if the dependencies finished its execution
        @returns : - None -> no more tasks to be executed
                   - JobXXX
        """
        if self._stop_running:
            return None  # gentle stop
        node = completed
        while True:
            # get next task from controller
            try:
                node = self.task_dispatcher.generator.send(node)
                if node == "hold on":
                    self.free_proc += 1
                    return JobHold()
            # no more tasks from controller...
            except StopIteration:
                # ... terminate one sub process if no other task waiting
                return None

            # send a task to be executed
            if self.select_task(node, self.tasks):
                # If sub-process already contains the Task object send
                # only safe pickle data, otherwise send whole object.
                task = node.task
                if task.loader is DelayedLoaded and self.Child == Process:
                    return JobTask(task)
                else:
                    return JobTaskPickle(task)


    def _run_tasks_init(self, task_dispatcher):
        """initialization for run_tasks"""
        self.task_dispatcher = task_dispatcher
        self.tasks = task_dispatcher.tasks


    def _run_start_processes(self, job_q, result_q):
        """create and start sub-processes
        @param job_q: (multiprocessing.Queue) tasks to be executed
        @param result_q: (multiprocessing.Queue) collect task results
        @return list of Process
        """
        # #### DEBUG PICKLE ERRORS
        # class MyPickler (pickle._Pickler):
        #     def save(self, obj):
        #         print('pickling object {} of type {}'.format(obj, type(obj)))
        #         try:
        #             Pickler.save(self, obj)
        #         except:
        #             print('error. skipping...')
        # from io import BytesIO
        # pickler = MyPickler(BytesIO())
        # pickler.dump(self)
        # ### END DEBUG

        proc_list = []
        for _ in range(self.num_process):
            next_job = self.get_next_job(None)
            if next_job is None:
                break  # do not start more processes than tasks
            job_q.put(next_job)
            process = self.Child(
                target=self.execute_task_subprocess,
                args=(job_q, result_q, self.reporter.__class__))
            process.start()
            proc_list.append(process)
        return proc_list

    def _process_result(self, node, task, result):
        """process result received from sub-process"""
        base_fail = result.get('failure')
        task.update_from_pickle(result['task'])
        for action, output in zip(task.actions, result['out']):
            action.out = output
        for action, output in zip(task.actions, result['err']):
            action.err = output
        self.process_task_result(node, base_fail)


    def run_tasks(self, task_dispatcher):
        """controls subprocesses task dispatching and result collection
        """
        # result queue - result collected from sub-processes
        result_q = self.Queue()
        # task queue - tasks ready to be dispatched to sub-processes
        job_q = self.Queue()
        self._run_tasks_init(task_dispatcher)
        proc_list = self._run_start_processes(job_q, result_q)

        # wait for all processes terminate
        proc_count = len(proc_list)
        try:
            while proc_count:
                # wait until there is a result to be consumed
                result = result_q.get()

                if 'exit' in result:
                    raise result['exit'](result['exception'])
                node = task_dispatcher.nodes[result['name']]
                task = node.task
                if 'reporter' in result:
                    getattr(self.reporter, result['reporter'])(task)
                    continue
                self._process_result(node, task, result)

                # update num free process
                free_proc = self.free_proc + 1
                self.free_proc = 0
                # tries to get as many tasks as free process
                completed = node
                for _ in range(free_proc):
                    next_job = self.get_next_job(completed)
                    completed = None
                    if next_job is None:
                        proc_count -= 1
                    job_q.put(next_job)
                # check for cyclic dependencies
                assert len(proc_list) > self.free_proc
        except (SystemExit, KeyboardInterrupt, Exception):
            if self.Child == Process:
                for proc in proc_list:
                    proc.terminate()
            raise
        # we are done, join all process
        for proc in proc_list:
            proc.join()

        # get teardown results
        while not result_q.empty():  # safe because subprocess joined
            result = result_q.get()
            assert 'reporter' in result
            task = task_dispatcher.tasks[result['name']]
            getattr(self.reporter, result['reporter'])(task)


    def execute_task_subprocess(self, job_q, result_q, reporter_class):
        """executed on child processes
        @param job_q: task queue,
            * None elements indicate process can terminate
            * JobHold indicate process should wait for next task
            * JobTask / JobTaskPickle task to be executed
        """
        self.result_q = result_q
        if self.Child == Process:
            self.reporter = MReporter(self, reporter_class)
        try:
            while True:
                job = job_q.get()

                if job is None:
                    self.teardown()
                    return  # no more tasks to execute finish this process

                # job is an incomplete Task obj when pickled, attrbiutes
                # that might contain unpickleble data were removed.
                # so we need to get task from this process and update it
                # to get dynamic task attributes.
                if job.type is JobTaskPickle.type:
                    task = self.tasks[job.name]
                    if self.Child == Process:  # pragma: no cover ...
                        # ... actually covered but subprocess doesnt get it.
                        task.update_from_pickle(job.task_dict)

                elif job.type is JobTask.type:
                    task = pickle.loads(job.task_pickle)

                # do nothing. this is used to start the subprocess even
                # if no task is available when process is created.
                else:
                    assert job.type is JobHold.type
                    continue  # pragma: no cover

                result = {'name': task.name}
                task_failure = self.execute_task(task)
                if task_failure:
                    result['failure'] = task_failure
                result['task'] = task.pickle_safe_dict()
                result['out'] = [action.out for action in task.actions]
                result['err'] = [action.err for action in task.actions]

                result_q.put(result)
        except (SystemExit, KeyboardInterrupt, Exception) as exception:
            # error, blow-up everything. send exception info to master process
            result_q.put({
                'exit': exception.__class__,
                'exception': str(exception)})
