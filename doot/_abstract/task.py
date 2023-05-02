
"""Tasks are the main abstractions managed by doot"""

import os
import sys
import inspect
from collections import OrderedDict
from collections.abc import Callable
from pathlib import PurePath

# used to indicate that a task had DelayedLoader but was already created
DelayedLoaded = False

class DootTask_i:
    """
    holds task information and state, and executes it
    """
    DEFAULT_VERBOSITY = 1
    string_types = (str, )
    # list of valid types/values for each task attribute.
    valid_attr = {'basename': (string_types, ()),
                  'name': (string_types, ()),
                  'actions': ((list, tuple), (None,)),
                  'file_dep': ((list, tuple), ()),
                  'task_dep': ((list, tuple), ()),
                  'uptodate': ((list, tuple), ()),
                  'calc_dep': ((list, tuple), ()),
                  'targets': ((list, tuple), ()),
                  'setup': ((list, tuple), ()),
                  'clean': ((list, tuple), (True,)),
                  'teardown': ((list, tuple), ()),
                  'doc': (string_types, (None,)),
                  'params': ((list, tuple,), ()),
                  'pos_arg': (string_types, (None,)),
                  'verbosity': ((), (None, 0, 1, 2,)),
                  'io': ((dict,), (None,)),
                  'getargs': ((dict,), ()),
                  'title': ((Callable,), (None,)),
                  'watch': ((list, tuple), ()),
                  'meta': ((dict,), (None,))
                  }

    def __init__(self, name, actions, file_dep=(), targets=(),
                 task_dep=(), uptodate=(),
                 calc_dep=(), setup=(), clean=(), teardown=(),
                 subtask_of=None, has_subtask=False,
                 doc=None, params=(), pos_arg=None,
                 verbosity=None, io=None, title=None, getargs=None,
                 watch=(), meta=None, loader=None):
        pass

    def __repr__(self):
        return f"<Task: {self.name}>"

    def __getstate__(self):
        """
        remove attributes that never used on process that only execute tasks
        """
        to_pickle = self.__dict__.copy()
        # never executed in sub-process
        to_pickle['uptodate'] = None
        to_pickle['value_savers'] = None
        # can be re-recreated on demand
        to_pickle['_action_instances'] = None
        return to_pickle

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        return self.name < other.name

    def update_deps(self, deps):
        pass

    def init_options(self, args=None):
        pass

    @staticmethod
    def check_attr(task, attr, value, valid):
        if isinstance(value, valid[0]):
            return
        if value in valid[1]:
            return

        # input value didnt match any valid type/value, raise exception
        msg = "Task '%s' attribute '%s' must be " % (task, attr)
        accept = ", ".join([getattr(v, '__name__', str(v)) for v in
                            (valid[0] + valid[1])])
        msg += "{%s} got:%r %s" % (accept, value, type(value))
        raise InvalidTask(msg)

    @property
    def actions(self):
        """lazy creation of action instances"""
        pass

    def save_extra_values(self):
        """run value_savers updating self.values"""
        pass

    def overwrite_verbosity(self, stream):
        pass

    def __call__(self, stream):
        """Executes the task.
        @return failure: see CmdAction.execute
        """
        pass

    def teardown(self, stream):
        pass

    def clean(self, outstream, dryrun):
        pass

    def title(self):
        pass

    def pickle_safe_dict(self):
        """remove attributes that might contain unpickleble content
        mostly probably closures
        """
        pass

    def update_from_pickle(self, pickle_obj):
        """update self with data from pickled Task"""
        pass
