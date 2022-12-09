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


def task_tags_init():
    """:: initalise gtags """
    return {
        "actions" : [ f"gtags -C {src_dir} ." ],
        "targets" : [ src_dir / "GPATH",
                      src_dir / "GRTAGS",
                      src_dir / "GTAGS" ],
        "basename" : "_tags_init",
    }


def task_tags():
    """:: update tag files """
    return {
        "actions"  : [],
        "file_dep" : [ src_dir / "GPATH",
                       src_dir / "GRTAGS",
                       src_dir / "GTAGS" ],
    }
