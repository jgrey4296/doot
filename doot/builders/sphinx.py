##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml, doc_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup
from doot.files.clean_dirs import clean_target_dirs

##-- end imports

__all__ = [
        "SphinxDocTask", "task_browse",

]

sphinx_build_dir = build_dir / "sphinx"

##-- dir check
check_dir = CheckDir(paths=[sphinx_build_dir ], name="sphinx", task_dep=["_checkdir::build"])
##-- end dir check

builder    = data_toml.or_get("html").tool.doot.sphinx

class SphinxDocTask:

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self) -> dict:
        """:: Build sphinx documentation """

        cmd  = "sphinx-build"
        args = ['-b', builder,
                docs_dir,
                sphinx_build_dir,
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



    def gen_toml(self):
        return """
##-- sphinx
[tool.doot.sphinx]
builder   = "html"
verbosity = 0
##-- end sphinx
"""

def task_browse() -> dict:
    """:: Task definition """
    cmd  = "open"
    args = [ build_dir / "html" / "index.html" ]

    return {
        "basename"    : "sphinx::browse",
        "actions"     : [build_cmd(cmd, args)],
        "task_dep"    : ["sphinx::build"],
    }

