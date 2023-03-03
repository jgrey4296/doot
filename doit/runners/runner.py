"""Task runner"""

from multiprocessing import Process, Queue as MQueue
from threading import Thread
import pickle
import queue

from .exceptions import InvalidTask, BaseFail
from .exceptions import TaskFailed, SetupError, DependencyError, UnmetDependency
from .task import Stream, DelayedLoaded

# execution result.
SUCCESS = 0
FAILURE = 1
ERROR = 2

class Runner():
    """Task runner

    run_all()
      run_tasks():
        for each task:
            select_task()
            execute_task()
            process_task_result()
      finish()

    """

    def __init__(self, dep_manager, reporter, continue_=False,
                 always_execute=False, stream=None):
        """
        @param dep_manager: DependencyBase
        @param reporter: reporter object to be used
        @param continue_: (bool) execute all tasks even after a task failure
        @param always_execute: (bool) execute even if up-to-date or ignored
        @param stream: (task.Stream) global verbosity
        """
        self.dep_manager = dep_manager
        self.reporter = reporter
        self.continue_ = continue_
        self.always_execute = always_execute
        self.stream = stream if stream else Stream(0)

        self.teardown_list = []  # list of tasks to be teardown
        self.final_result = SUCCESS  # until something fails
        self._stop_running = False

    def _handle_task_error(self, node, base_fail):
        """handle all task failures/errors

        called whenever there is an error before executing a task or
        its execution is not successful.
        """
        assert isinstance(base_fail, BaseFail)
        node.run_status = "failure"
        self.dep_manager.remove_success(node.task)
        self.reporter.add_failure(node.task, base_fail)
        # only return FAILURE if no errors happened.
        if isinstance(base_fail, TaskFailed) and self.final_result != ERROR:
            self.final_result = FAILURE
        else:
            self.final_result = ERROR
        if not self.continue_:
            self._stop_running = True

    def _get_task_args(self, task, tasks_dict):
        """get values from other tasks"""
        task.init_options()

        def get_value(task_id, key_name):
            """get single value or dict from task's saved values"""
            if key_name is None:
                return self.dep_manager.get_values(task_id)
            return self.dep_manager.get_value(task_id, key_name)

        # selected just need to get values from other tasks
        for arg, value in task.getargs.items():
            task_id, key_name = value

            if tasks_dict[task_id].has_subtask:
                # if a group task, pass values from all sub-tasks
                arg_value = {}
                base_len = len(task_id) + 1  # length of base name string
                for sub_id in tasks_dict[task_id].task_dep:
                    name = sub_id[base_len:]
                    arg_value[name] = get_value(sub_id, key_name)
            else:
                arg_value = get_value(task_id, key_name)
            task.options[arg] = arg_value

    def select_task(self, node, tasks_dict):
        """Returns bool, task should be executed
         * side-effect: set task.options

        Tasks should be executed if they are not up-to-date.

        Tasks that contains setup-tasks must be selected twice,
        so it gives chance for dependency tasks to be executed after
        checking it is not up-to-date.
        """
        task = node.task

        # if run_status is not None, it was already calculated
        if node.run_status is None:

            self.reporter.get_status(task)

            # overwrite with effective verbosity
            task.overwrite_verbosity(self.stream)

            # check if task should be ignored (user controlled)
            if node.ignored_deps or self.dep_manager.status_is_ignore(task):
                node.run_status = 'ignore'
                self.reporter.skip_ignore(task)
                return False

            # check task_deps
            if node.bad_deps:
                bad_str = " ".join(n.task.name for n in node.bad_deps)
                self._handle_task_error(node, UnmetDependency(bad_str))
                return False

            # check if task is up-to-date
            res = self.dep_manager.get_status(task, tasks_dict)
            if res.status == 'error':
                msg = "ERROR: Task '{}' checking dependencies: {}".format(
                    task.name, res.get_error_message())
                self._handle_task_error(node, DependencyError(msg))
                return False

            # set node.run_status
            if self.always_execute:
                node.run_status = 'run'
            else:
                node.run_status = res.status

            # if task is up-to-date skip it
            if node.run_status == 'up-to-date':
                self.reporter.skip_uptodate(task)
                task.values = self.dep_manager.get_values(task.name)
                return False

            if task.setup_tasks:
                # dont execute now, execute setup first...
                return False
        else:
            # sanity checks
            assert node.run_status == 'run', \
                "%s:%s" % (task.name, node.run_status)
            assert task.setup_tasks

        try:
            self._get_task_args(task, tasks_dict)
        except Exception as exception:
            msg = ("ERROR getting value for argument\n" + str(exception))
            self._handle_task_error(node, DependencyError(msg))
            return False

        return True

    def execute_task(self, task):
        """execute task's actions"""
        # register cleanup/teardown
        if task.teardown:
            self.teardown_list.append(task)

        # finally execute it!
        self.reporter.execute_task(task)
        return task.execute(self.stream)

    def process_task_result(self, node, base_fail):
        """handles result"""
        task = node.task
        # save execution successful
        if base_fail is None:
            task.save_extra_values()
            try:
                self.dep_manager.save_success(task)
            except FileNotFoundError as exception:
                msg = (f"ERROR: Task '{task.name}' saving success: "
                       f"Dependent file '{exception.filename}' does not exist.")
                base_fail = DependencyError(msg)
            else:
                node.run_status = "successful"
                self.reporter.add_success(task)
                return
        # task error
        self._handle_task_error(node, base_fail)

    def run_tasks(self, task_dispatcher):
        """This will actually run/execute the tasks.
        It will check file dependencies to decide if task should be executed
        and save info on successful runs.
        It also deals with output to stdout/stderr.

        @param task_dispatcher: L{TaskDispacher}
        """
        node = None
        while True:
            if self._stop_running:
                break

            try:
                node = task_dispatcher.generator.send(node)
            except StopIteration:
                break

            if not self.select_task(node, task_dispatcher.tasks):
                continue

            base_fail = self.execute_task(node.task)
            self.process_task_result(node, base_fail)

    def teardown(self):
        """run teardown from all tasks"""
        for task in reversed(self.teardown_list):
            self.reporter.teardown_task(task)
            result = task.execute_teardown(self.stream)
            if result:
                msg = "ERROR: task '%s' teardown action" % task.name
                error = SetupError(msg, result)
                self.reporter.cleanup_error(error)

    def finish(self):
        """finish running tasks"""
        # flush update dependencies
        self.dep_manager.close()
        self.teardown()

        # report final results
        self.reporter.complete_run()
        return self.final_result

    def run_all(self, task_dispatcher):
        """entry point to run tasks
        @ivar task_dispatcher (TaskDispatcher)
        """
        try:
            if hasattr(self.reporter, 'initialize'):
                self.reporter.initialize(task_dispatcher.tasks,
                                         task_dispatcher.selected_tasks)
            self.run_tasks(task_dispatcher)
        except InvalidTask as exception:
            self.reporter.runtime_error(str(exception))
            self.final_result = ERROR
        finally:
            self.finish()
        return self.final_result
