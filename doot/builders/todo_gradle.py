##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports
# https://docs.gradle.org/current/userguide/command_line_interface.html
## create build.grade, run tasks, create logging.properties

def task_is_gradle():
    return {
        "file_dep" : ["build.gradle"]
    }

def task_gradle_init():
    pass

def task_gradle_build():
    pass

def task_gradle_assemble():
    pass

def task_gradle_check():
    pass

def task_gradle_clean():
    pass

def task_gradle_javadoc():
    pass

def task_gradle_logging():
    pass

def task_gradle_version():
    pass
