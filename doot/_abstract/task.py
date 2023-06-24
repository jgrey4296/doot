
"""Tasks are the main abstractions managed by doot"""
from __future__ import annotations
import os
import sys
import inspect
from collections import OrderedDict
from collections.abc import Callable
from pathlib import PurePath
from doot._abstract.control import TaskOrdering_i

class Task_i(TaskOrdering_i):
    """
    holds task information and state, and executes it
    """

    def __init__(self, name, *args, **kwargs):
        raise NotImplementedError()

    def __repr__(self):
        return f"<Task: {self.name}>"

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        return self.name < other.name

    @property
    def actions(self):
        """lazy creation of action instances"""
        raise NotImplementedError()

    def __call__(self, stream):
        """Executes the task. """
        raise NotImplementedError()

    def teardown(self, stream):
        raise NotImplementedError()

    def clean(self):
        raise NotImplementedError()
