##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber
##-- end imports

plant_dir = build_dir / "plantuml"

##-- dir check
plant_check = CheckDir(paths=[plant_dir], name="plantuml", task_dep=["_checkdir::build"])

##-- end dir check

class PlantUMLGlobberTask(globber.FileGlobberMulti):
    """
    run plantuml on a specification, generating target.'ext's
    """

    def __init__(self):
        super().__init__("plantuml::png", [".plantuml"], [build_dir], rec=True)

    def build_action(self, fpath):
        cmd        = "plantuml"
        args       = ["-tpng",
                      "-output", plant_dir.resolve(),
                      "-filename", "{targets}",
                      "{dependencies}"
                      ]
        return [build_cmd(cmd, args)]

    def subtask_detail(self, fpath, task):
        targ_fname = fpath.with_suffix(".png")
        task.update({"actions"  : [ build_cmd(cmd, args)],
                     "targets"  : [ plant_dir / targ_fname.name],
                     "file_dep" : [ fpath ],
                     "task_dep" : [ f"plantuml::check:{task['name']}" ],
                     "params"   : [ { "name"    : "ext", "short"   : "e", "type"    : str, "default" : "png" },],
                     "clean"     : True,
                     })
        return task

class PlantUMLGlobberText(globber.FileGlobberMulti):
    """
    run plantuml on a spec for text output
    """

    def __init__(self):
        super().__init__("plantuml::txt", [".plantuml"], [build_dir], rec=True)

    def subtask_detail(self, fpath, task):
        cmd  = "plantuml"
        args = ["-ttxt",
                "-output", plant_dir.resolve(),
                "-filename", "{targets}",
                "{dependencies}"
                ]
        targ_fname = fpath.with_suffix(".atxt")
        task.update({
            "actions"  : [ build_cmd(cmd, args)],
            "targets"  : [ plant_dir / targ_fname.name],
            "file_dep" : [ fpath ],
            "task_dep" : [ f"plantuml::check:{task['name']}" ],
            "clean"    : True,
        })
        return task

class PlantUMLGlobberCheck(globber.FileGlobberMulti):
    """
    check syntax of plantuml files
    """

    def __init__(self):
        super().__init__("plantuml::check", [".plantuml"], [build_dir], rec=True)

    def subtask_detail(self, fpath, task):
        cmd        = "plantuml"
        args       = [ "-checkonly", "{dependencies}"]
        task.update({
            "actions"  : [ build_cmd(cmd, args)],
            "file_dep" : [ fpath ],
            "uptodate" : [False],
        })
        return task
