
##-- imports
from __future__ import annotations

import datetime
import logging as logmod
import pathlib as pl
import zipfile
from doit.task import Task as DoitTask

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.loc_data import DootLocData
from doot.utils.tasker import DootTasker
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


__all__ = [
        "ZipTask"
]

class ZipTask(DootTasker):
    """
    (-> temp) Automate creation of archive zipfiles
    will be named `zip::{name/default}`
    specify `paths` and/or `globs`,
    set `data` to True or a datetime.strftime format to customize naming
    (time is based on task creation time, not task execution time)

    target : zipfile name to put into temp
    root   : the root filesystem path to relativize every zip content against
    paths  : explicit file adds
    globs  : general adds
    date   : format of adding a date to target name
    to_build_dir : if true, moves the zipfile to build when complete

    TODO timeout={int} for rebuilding if target zip is hours? days? too old?
    TODO add filter_fn
    """

    def __init__(self, base:str="ziptask::default", dirs:DootLocData=None, target:str, root:pl.Path, paths:list[pl.Path]=None, globs:list[str]=None,  date:bool|str=False, to_build_dir=False):
        super().__init__(base, dirs)
        self.date     : bool | str = date
        self.target : str          = pl.Path(target)
        self.root                  = root
        self.paths                 = paths or []
        self.globs    : list[str]  = globs or []
        self.to_build_dir : bool   = to_build_dir

    def clean(self, task):
        """
        delete all zip files matching the stem, regardless of additional date
        """
        target = pl.Path(task.targets[0])
        zip_base = target.parent
        zip_stem = target.stem

        print(f"Cleaning {zip_base}/{zip_stem}*.zip")
        for zipf in zip_base.glob(f"{zip_stem}*.zip"):
            zipf.unlink()

        target.unlink(missing_ok=True)

    def task_detail(self, task) -> dict:
        task.update({
            "actions"  : [ self.action_zip_create, self.action_zip_add_paths, self.action_zip_globs],
            "teardown" : [self.action_move_zip],
            "targets"  : [ self.dirs.temp / self.dated_target().name ],
            "file_dep" : self.paths,
            "task_dep" : [ self.dirs.checker ],
            })
        task['meta'].update({"globs" : self.globs,})
        return task


    def dated_target(self):
        target_stem = self.target.stem
        match self.date:
            case False:
                pass
            case True:
                now         = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
                target_stem = f"{target.stem}-{now}"
            case str():
                now         = datetime.datetime.strftime(datetime.datetime.now(), date)
                target_stem = f"{target.stem}-{now}"

        return self.target.with_stem(target_stem)


    def action_zip_create(self, task:DoitTask):
        target = pl.Path(task.targets[0])
        if target.exists():
            target.unlink()

        now = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
        record_str = f"Zip File created at {now} for doot task: {task.name}"

        with zipfile.ZipFile(target, 'w') as targ:
            targ.writestr(".taskrecord", record_str)

    def action_zip_add_paths(self, task:DoitTask, dependencies):
        assert(all(pl.Path(x).exists() for x in dependencies))
        target = pl.Path(task.targets[0])
        with zipfile.ZipFile(target, 'a') as targ:
            for dep in dependencies:
                if pl.Path(dep).name[0] == ".":
                    continue
                targ.write(str(dep), pl.Path(dep).relative_to(self.root))

    def action_zip_globs(self, task):
        logging.debug(f"Globbing: {task.meta['globs']}")
        cwd = pl.Path()
        target = pl.Path(task.targets[0])
        with zipfile.ZipFile(target, 'a') as targ:
            for glob in task.meta['globs']:
                result = list(cwd.glob(glob))
                print(f"Globbed: {cwd}[{glob}] : {len(result)}")
                for dep in result:
                    # if pl.Path(dep).name[0] == ".":
                    #     continue
                    targ.write(str(dep), pl.Path(dep).relative_to(self.root))

    def action_move_zip(self, task):
        if not self.to_build_dir:
            return

        target = pl.Path(task.targets[0])
        assert(not (self.dirs.build / target.name).exists())
        target.rename(self.dirs.build / target.name)
