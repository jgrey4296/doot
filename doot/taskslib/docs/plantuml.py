##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial

import doot
from doot import globber
##-- end imports


class PlantUMLGlobberTask(globber.EagerFileGlobber):
    """
    ([visual] -> build) run plantuml on a specification, generating target.'ext's
    """

    def __init__(self, name=None, dirs:DootLocData=None, roots:list[pl.Path]=None, fmt="png", rec=True):
        assert(roots or 'visual' in dirs.extra)
        name = name or f"plantuml::{fmt}"
        super().__init__(name, dirs, roots or [dirs.src], exts=[".plantuml"], rec=True)
        self.fmt       = fmt

    def subtask_detail(self, task, fpath=None):
        targ_fname = fpath.with_suffix(f".{self.fmt}")
        task.update({"targets"  : [ self.dirs.build / targ_fname.name],
                     "file_dep" : [ fpath ],
                     "task_dep" : [ f"plantuml::check:{task['name']}" ],
                     "clean"     : True,
                     })
        task['actions'] += self.subtask_actions(fpath)
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

    def __init__(self, name="plantuml::check", dirs=None, roots:list[pl.Path]=None, rec=True):
        assert(roots or 'visual' in dirs.extra)
        super().__init__(name, dirs, roots or [dirs.extra['visual']], exts=[".plantuml"], rec=rec)

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ fpath ],
            "uptodate" : [ False ],
        })
        task['actions'] += self.subtask_actions(fpath)

        return task

    def subtask_actions(self, fpath):
        return [ CmdAction([self.check_action], shell=False) ]

    def check_action(self, dependencies):
        return ["plantuml", "-checkonly", *dependencies]
