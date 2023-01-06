##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber
##-- end imports


class PlantUMLGlobberTask(globber.EagerFileGlobber):
    """
    ([visual] -> build) run plantuml on a specification, generating target.'ext's
    """

    def __init__(self, dirs:DootLocData, roots:list[pl.Path]=None, fmt="png"):
        assert(roots or 'visual' in dirs.extra)
        super().__init__(f"plantuml::{ext}", dirs, roots or [dirs.extra['visual']], exts=[".plantuml"], rec=True)
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


class PlantUMLGlobberCheck(globber.EagerFileGlobber):
    """
    ([visual]) check syntax of plantuml files
    TODO Adapt godot::check pattern
    """

    def __init__(self, dirs, roots:list[pl.Path]):
        assert(roots or 'visual' in dirs.extra)
        super().__init__("plantuml::check", dirs, roots or [dirs.extra['visual']], exts=[".plantuml"], rec=True)

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
