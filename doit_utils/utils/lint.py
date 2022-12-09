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


def task_initpy() -> dict:
    """:: touch all __init__.py files """
	# TODO find ${PY_TOP} -type d -print0 | xargs -0 -I {} touch "{}/__init__.py"

    cmd  = ""
    args = []
    return {
        ## Required (callable | tuple(callable, *args, **kwargs))
        "actions"     : [ build_cmd(cmd, args) ],
    }

def task_lint() -> dict:
    """:: lint the package """
    # TODO add ignore / ignore-patterns / --ignore-paths

    data = pyproject['tool']['doit']['commands']['lint']
    cmd  = data['executable']
    args = [
        "--output-format", data['outfmt'],
        "--output", data['outfile'],
        "-E" if data['errors'] else "",
        pyproject['project']['name']
    ]


    return {
        "actions"   : [ build_cmd(cmd, args) ],
        "verbosity" : 2,
        "targets"   : [ "package.lint" ],
        "clean"     : True,
    }
