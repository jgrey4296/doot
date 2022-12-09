##-- imports
from __future__ import annotations
import pathlib as pl
import shutil

from doit import create_after
from doit.action import CmdAction
from doit.tools import (Interactive, PythonInteractiveAction, create_folder,
                        set_trace)

try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml
##-- end imports

def task_base_dircheck():
    """:: Create directories if they are missing """
    make = "mkdir -p %(targets)s"
    echo = "echo making %(targets)s"
    return {
        "actions"  : [ CmdAction(f"{make}; {echo}") ],
        "targets"  : [ build_dir ],
        "uptodate" : [ lambda task: all([pl.Path(x).exists() for x in task.targets]) ],
        "clean"    : [ force_clean_targets],
        "basename" : "_base-dircheck",
    }
