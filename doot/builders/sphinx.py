##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

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

builder    = data_toml.or_get("html").tool.doot.sphinx.builder()
verbosity  = int(data_toml.or_get("0").tool.door.sphinx.verbosity())

class SphinxDocTask:

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self) -> dict:
        """:: Build sphinx documentation """

        return {
            "basename" : "sphinx::build",
            "actions"  : [ self.sphinx_command() ],
            "task_dep" : ["_checkdir::sphinx"],
            "file_dep" : [ doc_dir / "conf.py" ],
            "targets"  : [ sphinx_build_dir ],
            "clean"    : [ clean_target_dirs ],
        }


    def sphinx_command(self):
        verbose = []
        match verbosity:
            case x if x > 0:
                verbose += ["-v" for i in range(x)]
            case x if x == -1:
                verbose.append("-q")
            case x if x == -2:
                verbose.append("-Q")

        return CmdAction(["sphinx-build", '-b', builder, doc_dir, sphinx_build_dir] + verbose,
                         shell=False)


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
    return {
        "basename"    : "sphinx::browse",
        "actions"     : [ CmdAction([ "open",  build_dir / "html" / "index.html" ], shell=False) ],
        "task_dep"    : ["sphinx::build"],
    }

