##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask

##-- end imports

def task_list_target(targ:str, target:pl.Path, dirs:DootLocData):
    """
    (-> build )list all files in the targ directory,
    to the build_dir/allfiles.report
    """
    def action(targets):
        files  = [x for x in target.glob("**/*") if not any([y in str(x) for y in ['.git', '.DS_Store', "__pycache__"]])]
        report = "\n".join(str(x) for x in files)
        for targ in targets:
            with open(targ, 'w') as f:
                f.write(report)

    return {
        "actions" : [ action ],
        "targets" : [ dirs.build / f"all_{targ}.report" ],
        "basename" : f"files::list.{targ}",
        "clean"   : True,
    }

