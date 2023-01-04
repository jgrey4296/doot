##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial

import doot
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber
##-- end imports


class PlantUMLGlobberTask(globber.FileGlobberMulti):
    """
    run plantuml on a specification, generating target.'ext's
    """

    def __init__(self, dirs:DootLocData, targets:list[pl.Path], fmt="png"):
        super().__init__(f"plantuml::{ext}", dirs, targets, exts=[".plantuml"], rec=True)
        self.fmt       = fmt

    def subtask_detail(self, fpath, task):
        targ_fname = fpath.with_suffix(f".{self.fmt}")
        task.update({"targets"  : [ self.dirs.build / targ_fname.name],
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

    def __init__(self, dirs, targets:list[pl.Path]):
        super().__init__("plantuml::check", dirs, targets, exts=[".plantuml"], rec=True)

    def subtask_detail(self, fpath, task):
        task.update({
            "file_dep" : [ fpath ],
            "uptodate" : [ False ],
        })
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction([self.check_action], shell=False) ]

    def check_action(self, dependencies):
        return ["plantuml", "-checkonly", *dependencies]
