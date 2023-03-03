"""extra goodies to be used in dodo files"""

import os
import time as time_module
import datetime
import json
import hashlib
import operator
import subprocess

from . import exceptions
from .action import CmdAction, PythonAction
from .task import result_dep  # imported for backward compatibility
result_dep  # pyflakes

def normalize_callable(ref):
    """return a list with (callable, *args, **kwargs)
    ref can be a simple callable or a tuple
    """
    if isinstance(ref, tuple):
        return list(ref)
    return [ref, (), {}]

# action

def create_folder(dir_path):
    """create a folder in the given path if it doesnt exist yet."""
    os.makedirs(dir_path, exist_ok=True)

# title

def title_with_actions(task):
    """return task name task actions"""
    if task.actions:
        title = "\n\t".join([str(action) for action in task.actions])
    # A task that contains no actions at all
    # is used as group task
    else:
        title = "Group: %s" % ", ".join(task.task_dep)
    return "%s => %s" % (task.name, title)

# uptodate

def run_once(task, values):
    """execute task just once
    used when user manually manages a dependency
    """

    def save_executed():
        return {'run-once': True}
    task.value_savers.append(save_executed)
    return values.get('run-once', False)

# uptodate

def set_trace():  # pragma: no cover
    """start debugger, make sure stdout shows pdb output.
    output is not restored.
    """
    import pdb
    import sys
    debugger = pdb.Pdb(stdin=sys.__stdin__, stdout=sys.__stdout__)
    debugger.set_trace(sys._getframe().f_back)  # pylint: disable=W0212

