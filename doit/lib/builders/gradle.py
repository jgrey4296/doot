# -*- mode:doit; -*-
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files

import doot
##-- end imports

# https://docs.gradle.org/current/userguide/command_line_interface.html
## create build.grade, run tasks, create logging.properties

from doot import tasker
from doot.tasks.utils.gradle import GradleMixin

data_path               = files("doot.__templates")
log_properties_template = data_path.joinpath("gradle_logging")

def task_gradle_logging():
    """:: generate a logging.properties file """

    def make_logging_properties(targets):
        pl.Path(targets[0]).write_text(log_properties_template.read_text())

    return {
        "basename" : "gradle::log",
        "actions"  : [ make_logging_properties ],
        "targets"  : [ "logging.properties" ],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_version():
    """:: get the current gradle version """

    return {
        "basename" : "gradle::version",
        "actions"  : [ CmdAction(["./gradlew", " --version"], shell=False) ],
        "file_dep" : ["build.gradle.kts"],
        "verbosity" : 2,
    }

def task_gradle_list():
    """
    list all gradle tasks that can be run
    """

    def cache_gradle_tasks(task, targets):
        pl.Path(targets[0]).write_text(task.values['result'])

    return {
        "basename" : "gradle::list",
        "actions"  : [ CmdAction(["./gradlew", ":tasks"], shell=False, save_out="result"),
                       cache_gradle_tasks,
                      ],
        "file_dep" : [ "build.gradle.kts" ],
        "targets"  : [ ".task_cache"  ],
        "verbosity" : 2,
    }

def task_gradle_projects():

    return {
        "basename" : "gradle::list",
        "actions"  : [ CmdAction(["./gradlew", ":projects"], shell=False) ],
        "file_dep" : [ "build.gradle.kts" ],
        "verbosity" : 2,
    }
