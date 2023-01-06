# -*- mode:doit; -*-
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
##-- end imports

# https://docs.gradle.org/current/userguide/command_line_interface.html
## create build.grade, run tasks, create logging.properties

##-- data
data_path               = files("doot.__templates")
log_properties_template = data_path.joinpath("gradle_logging")
##-- end data


def task_gradle_run():
    """:: run a program """

    return {
        "basename" : "gradle::run",
        "actions"  : [CmdAction(["./gradlew", "run"], shell=False)],
        "file_dep" : ["build.gradle.kts"],
        "verbosity": 2,
    }

def task_gradle_build():
    """:: run a gradle build """

    return {
        "basename" : "gradle::build",
        "actions"  : [CmdAction(["./gradlew", "build"], shell=False)],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_assemble():
    """:: the assemble task """

    return {
        "basename" : "gradle::assemble",
        "actions"  : [CmdAction(["./gradlew", "assemble"], shell=False)],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_check():
    """:: run gradle linting """

    return {
        "basename" : "gradle::check",
        "actions"  : [CmdAction(["./gradlew", "check"], shell=False)],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_clean():
    """:: clean the build directory """

    return {
        "basename" : "gradle::clean",
        "actions"  : [CmdAction(["./gradlew", "clean"], shell=False)],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_doc():
    """:: build javadocs"""

    return {
        "basename" : "gradle::doc",
        "actions"  : [CmdAction(["./gradlew", "javadoc"], shell=False)],
        "file_dep" : ["build.gradle.kts"],
    }

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

def task_gradle_test() -> dict:
    """:: run the project tests """
    return {
        "basename" : "gradle::test",
        "actions"  : [ CmdAction(["./gradlew", " test"], shell=False) ],
        "file_dep" : ["build.gradle.kts"],
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
