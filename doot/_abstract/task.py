
"""Tasks are the main abstractions managed by doot"""
##-- imports
from __future__ import annotations
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

    def __init__(self, name, *args, **kwargs):
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

    @property
    def actions(self):
        """lazy creation of action instances"""
        pass

    def __call__(self, stream):
        """Executes the task.
        """
        pass

    def teardown(self, stream):
        pass

    def clean(self):
        pass
