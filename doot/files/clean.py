##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml, src_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

py_cache_globs = ["**/*.pyc", "**/*.pyo", "**/.mypy_cache", "**/__pycache__", "**/flycheck_*.py"]
lisp_globs     = ["**/*.elc"]
mac_os_globs   = ["**/.DS_Store", "**/*~"]
java_globs     = ["**/*.class"]
log_globs      = ["**/log.*", "**/*.log"]

def clean_cache_globs(globs:list[str]):
    """
    Add to the 'clean' field of a task spec, call it with a list of glob strings
    """
    target_globs = globs
    def cleaner():
        to_remove = []
        for glob in globs:
            to_remove += src_dir.glob(glob)

        print(f"Removing: {len(to_remove)} targets from globs: ./{src_dir}:{globs}")
        for x in to_remove:
            if x.is_file():
                x.unlink()
            else:
                shutil.rmtree(x)

    return cleaner

