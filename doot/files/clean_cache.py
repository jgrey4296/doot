##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask

##-- end imports

py_cache_globs = ["**/*.pyc", "**/*.pyo", "**/.mypy_cache", "**/__pycache__", "**/flycheck_*.py"]
lisp_globs     = ["**/*.elc"]
mac_os_globs   = ["**/.DS_Store", "**/*~"]
java_globs     = ["**/*.class"]
log_globs      = ["**/log.*", "**/*.log"]


class CleanCacheAction:
    """
    add to the 'clean' field of a task spec
    trees = True will remove directories
    """

    def __init__(self, globs, trees=False):
        self.trees = trees
        self.globs = globs

    def __call__(self):
        to_remove = []
        for glob in globs:
            to_remove += src_dir.glob(glob)

        print(f"Removing: {len(to_remove)} targets from globs: ./{src_dir}:{globs}")
        for x in to_remove:
            if x.is_file():
                x.unlink()
            elif self.trees:
                shutil.rmtree(x)




