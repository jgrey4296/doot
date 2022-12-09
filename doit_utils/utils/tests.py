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


## TODO run in -X dev mode, add warnings
def task_test() -> dict:
    """:: Task definition """
    data = pyproject['tool']['doit']['commands']['test']
    cmd  = "python"
    args = ["-m", "unittest", "discover",
            pyproject['project']['name'],
            "-p", pyproject['tool']['doit']['commands']['test']['pattern'],
            "-t", pyproject['project']['name'],
            "-s", "{start}"
            ]

    if data['verbose']:
        args.append("-v")

    if data['failfast']:
        args.append('-f')

    return {
        ## Required (callable | tuple(callable, *args, **kwargs))
        "actions"     : [ build_cmd(cmd, args) ],
        "params"      : [ {"name"    : "start",
                           "start"   : "-s",
                           "default" : pyproject['project']['name']
                           },
                          ]
    }
