##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask

##-- end imports

glob_ignores = doot.config.or_get(['.git', '.DS_Store', "__pycache__"]).tool.doot.glob_ignores()

def task_list_target(targ:str, target:pl.Path, dirs:DootLocData):
    """
    (-> build )list all files in the targ directory,
    to the build_dir/allfiles.report
    """
    def action(targets):
        files  = [x for x in target.glob("**/*") if not any([y in str(x) for y in glob_ignores])]
        report = "\n".join(str(x) for x in files)
        with open(targets[0], 'w') as f:
            f.write(report)

    return {
        "actions" : [ action ],
        "targets" : [ dirs.build / f"all_{targ}.report" ],
        "basename" : f"files::list.{targ}",
        "clean"   : True,
    }

