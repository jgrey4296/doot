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

def task_fresh() -> dict:
    """:: Clean the logs and caches"""
    # find ${PY_TOP} -regextype posix-egrep -regex .*\(.mypy_cache\|__pycache__\|flycheck_.+\)$)
    # remove pyc's, pyo's, backups ("*~", "*.bak"),
    # remove generated .DS_Store, pickles, etc
    # .coverage, .tox, .cache etc
    return {"actions" : ['find . -maxdepth 1 -name "log.*" -exec rm {}']}
