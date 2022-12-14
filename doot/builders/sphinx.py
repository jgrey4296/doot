##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup

##-- end imports

class SphinxDocTask:

    sphinx_dir = "sphinx"

    def __init__(self, name="default", **kwargs):
        self.create_doit_tasks = self.build
        pass

    def build(self) -> dict:
        """:: Task definition """
        sphinx         = datatoml['tool']['sphinx']
        docs_dir       = sphinx['docs_dir']
        docs_build_dir = build_dir / docs_dir

        cmd  = "sphinx"
        args = ['-b', sphinx['builder'],
                docs_dir,
                docs_build_dir,
                ]

        match sphinx['verbosity']:
            case x if x > 0:
                args += ["-v" for i in range(x)]
            case x if x == -1:
                args.append("-q")
            case x if x == -2:
                args.append("-Q")

        return {
            "actions"  : [ build_cmd(cmd, args) ],
            "task_dep" : ["dircheck::sphinx"]
            "file_dep" : [ docs_dir / "conf.py" ],
        }


def task_browse() -> dict:
    """:: Task definition """
    cmd  = "open"
    args = [ build_dir / "html" / "index.html" ]

    return {
        "actions"     : [build_cmd(cmd, args)],
        "task_dep"    : ["sphinx::default"],
    }

##-- dir check
check_docs = CheckDir(paths=[build_dir / SphinxDocTask.sphinx_dir ], name="sphinx", task_dep=["checkdir::sphinx"],)
##-- end dir check
