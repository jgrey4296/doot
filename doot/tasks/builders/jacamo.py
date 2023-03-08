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

from os import environ
import shutil
import doot
from doot import tasker
from doot.mixins.commander import CommanderMixin
from doot.mixins.gradle import GradleMixin

jacamo_home = doot.config.on_fail(environ.get("JACAMO_HOME", None), str).jacamo.home(wrapper=pl.Path)

class JacamoNewProject(tasker.DootTasker, GradleMixin, CommanderMixin):
    """
    Create a new jacamo agent project
    """

    def __init__(self, name="jacamo::new", locs=doot.locs):
        super().__init__(name, locs)
        logging.debug("Using Jacamo Home: %s", jacamo_home)
        self.locs.ensure("src")

    def set_params(self):
        return [
            {"name": "project-name", "short": "n", "default": "jacamo_new", "type": str}
        ]

    def is_current(self, task):
        return (self.locs.root / "build.gradle.kts").exists()

    def setup_detail(self, task):
        task.update({
            "actions"  : [ self.initialise_gradle_root ],
            "targets"  : [ "build.gradle.kts", "settings.gradle.kts" ],
            "uptodate" : [ self.is_current ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                (self.log, [f"Adding New Jacamo Project: {self.locs.src}/{self.args['project-name']}", logmod.INFO]),
                self.cmd(jacamo_home / "scripts/jacamo-new-project", self.locs.src / self.args['project-name']),
                (self.add_project_to_gradle_settings, [self.locs.src / self.args['project-name']]),
            ],
        })
        return task

class JacamoRun(tasker.DootTasker, GradleMixin, CommanderMixin):
    """
    use gradle to run a jacamo agent
    """

    def __init__(self, name="jacamo::run", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            {"name": "project-name", "type": str, "default": None, "short": "n"}
        ]

    def task_detail(self, task):
        if not self.args['project-name']:
            return None

        run_task = self.gradle_subname(self.locs.src / self.args['project-name'] / "run")
        task.update({
            "actions": [
                self.call_gradle(run_task)
            ],
            "verbosity": 2,
        })
        return task

class JacamoBuild(tasker.DootTasker, CommanderMixin):
    """
    Build the jacamo project
    """

    def __init__(self, name="jacamo::build", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            {"name": "project-name", "type": str, "default": None, "short": "n"}
        ]

    def task_detail(self, task):
        if not self.args['project-name']:
            return None

        build_task = self.gradle_subname(self.locs.src / self.args['project-name'] / "build")
        task.update({
            "actions": [
                self.call_gradle(build_task),
            ],

        })
        return task
