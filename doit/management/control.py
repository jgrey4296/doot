"""Control tasks execution order"""
import fnmatch
from collections import deque
from collections import OrderedDict
import re

from .exceptions import InvalidTask, InvalidCommand, InvalidDodoFile
from .task import Task, DelayedLoaded
from .loader import generate_tasks

class RegexGroup:
    '''Helper to keep track of all delayed-tasks which regexp target
    matches the target specified from command line.
    '''
    def __init__(self, target, tasks):
        # target name specified in command line
        self.target = target
        # set of delayed-tasks names (string)
        self.tasks = tasks
        # keep track if the target was already found
        self.found = False


class TaskControl:
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
            regex_group = RegexGroup(filter_, set(delayed_matched_names))

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



