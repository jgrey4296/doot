##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

class GitLogTask:
    """
    Output a summary of the git repo, with a specific format
    see: https://git-scm.com/docs/git-log
    """
    report_dir = "reports"

    def __init__(self, fmt="%ai :: %h :: %al :: %s"):
        self.create_doit_tasks = self.build
        self.format = fmt

    def build(self):
        cmd = f"git log --pretty=format:\"{self.format}\"" + " > {targets}"
        return {
            "actions" : [ cmd ],
            "targets" : [build_dir / GitLogTask.report_dir / "full_git.log" ],
            "clean"   : True,
        }



##-- dir check
check_reports = CheckDir(paths=[build_dir / GitLogTask.report_dir ], name="git_reports", task_dep=["_checkdir::build"],)
##-- end dir check
