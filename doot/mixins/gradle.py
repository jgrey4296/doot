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
from doot import tasker, task_mixins

gradle = shutil.which("gradle")

class GradleMixin:

    def gradle_subname(self, name:pl.Path):
        return str(name).replace("/", ":")

    def call_gradle(self, *args):
        self.cmd(gradle, f"--project-cache-dir={self.locs.gradle.resolve()}",
                 *args)
        self.execute()

    def initialise_gradle_root(self):
        if (self.locs.root / "build.gradle.kts").exists():
            return

        logging.info("Setting up Root Gradle Project")
        self.call_gradle("init",
                         "--type", "basic",
                         "--dsl", "kotlin",
                         "--incubating",
                         "--project-name", self.locs.root.resolve().name,
                         )
        lines = [
            "rootProject.allprojects{",
            "    buildDir = File(\"${rootProject.projectDir}/.build/${project.name}\")",
            "}",
        ]

        with open(self.locs.root / "build.gradle.kts", "a") as f:
            print("\n".join(lines), file=f)

    def add_project_to_gradle_settings(self, fpath):
        # Add include(src:projName) to settings.gradle.kts
        project_name = self.gradle_subname(fpath)
        with open(self.locs.root / "settings.gradle.kts", 'a') as f:
            print(f"include(\"{project_name}\")", file=f)


    def gradle_doc(self):
        pass

    def gradle_clean(self):
        pass

    def gradle_test(self):
        pass

    def gradle_projects(self):
        pass

    def gradle_tasks(self):
        pass

    def gradle_check(self):
        pass
