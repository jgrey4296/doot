##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber
##-- end imports


def build_plantuml_cheks(plant_dir):
    plant_check = CheckDir(paths=[plant_dir],
                           name="plantuml",
                           task_dep=["_checkdir::build"])


class PlantUMLGlobberTask(globber.FileGlobberMulti):
    """
    run plantuml on a specification, generating target.'ext's
    """

    def __init__(self, targets:list[pl.Path], build_dir, fmt="png"):
        super().__init__(f"plantuml::{ext}", [".plantuml"], targets, rec=True)
        self.build_dir = build_dir
        self.fmt       = fmt

    def subtask_detail(self, fpath, task):
        targ_fname = fpath.with_suffix(f".{self.fmt}")
        task.update({"targets"  : [ plant_dir / targ_fname.name],
                     "file_dep" : [ fpath ],
                     "task_dep" : [ f"plantuml::check:{task['name']}" ],
                     "clean"     : True,
                     })
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(self.run_plantuml, shell=False) ]

    def run_plantuml(self, dependencies, targets):
        return ["plantuml", f"-t{self.fmt}",
                "-output", self.build_dir.resolve(),
                "-filename", targets[0],
                dependencies[0]
                ]


class PlantUMLGlobberCheck(globber.FileGlobberMulti):
    """
    check syntax of plantuml files
    TODO Adapt godot::check pattern
    """

    def __init__(self, targets:list[pl.Path]):
        super().__init__("plantuml::check", [".plantuml"], targets, rec=True)

    def subtask_detail(self, fpath, task):
        task.update({
            "file_dep" : [ fpath ],
            "uptodate" : [False],
        })
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction([self.check_action], shell=False) ]

    def check_action(self, dependencies):
        return ["plantuml", "-checkonly", *dependencies]
