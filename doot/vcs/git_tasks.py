##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports
report_dir = build_dir / "reports"

##-- dir check
check_reports = CheckDir(paths=[report_dir], name="git_reports", task_dep=["_checkdir::build"])
##-- end dir check

class GitLogTask:
    """
    Output a summary of the git repo, with a specific format
    see: https://git-scm.com/docs/git-log
    """

    def __init__(self, fmt="%ai :: %h :: %al :: %s"):
        self.create_doit_tasks = self.build
        self.format = fmt

    def build(self):
        cmd = f"git log --pretty=format:\"{self.format}\" " + " > {targets}"
        return {
            "basename" : "git::logs",
            "actions"  : [ cmd ],
            "targets"  : [ report_dir / "full_git.log" ],
            "task_dep" : [ "_checkdir::git_reports" ],
            "clean"    : True,
        }



