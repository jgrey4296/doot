
"""Tasks are the main abstractions managed by doot"""
from __future__ import annotations
from typing import Generator
from doot._abstract.control import TaskStatus_i

class Task_i(TaskStatus_i):
    """
    holds task information and state, and executes it
    """

    def __init__(self, name, *args, **kwargs):
        raise NotImplementedError()

    def __repr__(self):
        return f"<Task: {self.name}>"

    def __eq__(self, other):
        return self.name == other.name


    @property
    def actions(self) -> Generator:
        """lazy creation of action instances"""
        raise NotImplementedError()

    def __call__(self):
        """Executes the task. """
        raise NotImplementedError()
