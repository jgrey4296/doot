##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup
from doot.files.clean_dirs import clean_target_dirs

##-- end imports
sphinx_dir = build_dir / "sphinx"

__all__ = [
        "check_dir", "SphinxDocTask", "task_browse",

]

##-- dir check
check_dir = CheckDir(paths=[sphinx_dir ], name="sphinx", task_dep=["_checkdir::build"])
##-- end dir check

sphinx         = data_toml.tool.doot.sphinx

class SphinxDocTask:

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self) -> dict:
        """:: Build sphinx documentation """
        docs_dir       = pl.Path(sphinx.docs_dir)
        docs_build_dir = build_dir / docs_dir

        cmd  = "sphinx-build"
        args = ['-b', sphinx.builder,
                docs_dir,
                docs_build_dir,
                ]

        match sphinx.verbosity:
            case x if x > 0:
                args += ["-v" for i in range(x)]
            case x if x == -1:
                args.append("-q")
            case x if x == -2:
                args.append("-Q")

        return {
            "basename" : "sphinx::build",
            "actions"  : [ build_cmd(cmd, args) ],
            "task_dep" : ["_checkdir::sphinx"],
            "file_dep" : [ docs_dir / "conf.py" ],
            "targets"  : [ docs_build_dir ],
            "clean"    : [ clean_target_dirs ],
        }


def task_browse() -> dict:
    """:: Task definition """
    cmd  = "open"
    args = [ build_dir / "html" / "index.html" ]

    return {
        "basename"    : "sphinx::browse",
        "actions"     : [build_cmd(cmd, args)],
        "task_dep"    : ["sphinx::build"],
    }

