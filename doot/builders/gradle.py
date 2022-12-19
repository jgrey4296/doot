# -*- mode:doit; -*-
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports
# https://docs.gradle.org/current/userguide/command_line_interface.html
## create build.grade, run tasks, create logging.properties

def task_gradle_run():
    """:: run a program """

    return {
        "basename" : "gradle::run",
        "actions"  : ["./gradlew run"],
        "file_dep" : ["build.gradle.kts"],
        "verbosity": 2,
    }

def task_gradle_build():
    """:: run a gradle build """

    return {
        "basename" : "gradle::build",
        "actions"  : ["./gradlew build"],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_assemble():
    """:: the assemble task """

    return {
        "basename" : "gradle::assemble",
        "actions"  : ["./gradlew assemble"],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_check():
    """:: run gradle linting """

    return {
        "basename" : "gradle::check",
        "actions"  : ["./gradlew check"],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_clean():
    """:: clean the build directory """

    return {
        "basename" : "gradle::clean",
        "actions"  : ["./gradlew clean"],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_doc():
    """:: build javadocs"""

    return {
        "basename" : "gradle::doc",
        "actions"  : ["gradle javadoc"],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_logging():
    """:: generate a logging.properties file """

    return {
        "basename" : "gradle::log",
        "actions"  : [],
        "targets"  : [ "logging.properties" ],
        "file_dep" : ["build.gradle.kts"],
    }

def task_gradle_version():
    """:: get the current gradle version """

    return {
        "basename" : "gradle::version",
        "actions"  : ["./gradlew --version"],
        "file_dep" : ["build.gradle.kts"],
        "verbosity" : 2,
    }
def task_gradle_test() -> dict:
    """:: run the project tests """
    return {
        "basename" : "gradle::test",
        "actions"  : ["./gradlew test"],
        "file_dep" : ["build.gradle.kts"],
    }
