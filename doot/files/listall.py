##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml, src_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

def task_listall():
    """  list all files in the src directory,
    to the build_dir/allfiles.report
    """
    def action(targets):
        files  = [x for x in src_dir.glob("**/*") if ".git" not in str(x)]
        report = "\n".join(str(x) for x in files)
        for targ in targets:
            with open(targ, 'w') as f:
                f.write(report)

    return {
        "actions" : [ action ],
        "targets" : [ build_dir / "allfiles.report" ],
        "task_dep" : ["_checkdir::build"],
        "basename" : "files::listall",
    }
