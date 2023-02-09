
##-- imports
from __future__ import annotations

import datetime
import logging as logmod
import pathlib as pl
import sys
import zipfile
from doit.task import Task as DoitTask
from random import randint

import doot
from doot.loc_data import DootLocData
from doot.tasker import DootTasker
from doot.task_mixins import ActionsMixin, ZipperMixin
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


__all__ = [
        "ZipTask"
]

class ZipTask(DootTasker, ActionsMixin, ZipperMixin):
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

    def __init__(self, base:str="zip::default", locs:DootLocData=None, date:bool|str=False, pathsNglobs=None, overwrite=False):
        super().__init__(base, locs)
        self.date     : bool | str = date
        self.zip_overwrite         = overwrite
        self.output                = self.locs.build
        self.paths                 = (pathsNglobs or ([], []))[0]
        self.globs                 = (pathsNglobs or ([], []))[1]


    def clean(self, task):
        """
        delete all zip files matching the stem, regardless of additional date
        """
        target = pl.Path(task.targets[0])
        zip_base = target.parent
        zip_stem = target.stem

        logging.info(f"Cleaning {zip_base}/{zip_stem}*.zip")
        for zipf in zip_base.glob(f"{zip_stem}*.zip"):
            zipf.unlink()

        target.unlink(missing_ok=True)


    def task_setup(self, task):
        target_zip = self.zip_path()
        task.update({
            "actions": [ (self.zip_create, [target_zip])],
        })
        return task

    def task_detail(self, task) -> dict:
        temp_zip   = self.zip_path()
        task.update({
            "actions"  : [ (self.zip_add_paths, [temp_zip, *self.paths]),
                           (self.zip_globs,     [temp_zip, *self.globs]),
                          ],
            "targets"  : [ self.output / temp_zip.name ],
            "teardown" : [ (self.copy_to, (self.output, temp_zip), {"fn":"overwrite"}) ],
            "clean"    : [ (self.rmfiles, [self.output / temp_zip.name, temp_zip]) ],
            })
        return task

    def zip_path(self):
        zip_name   = self._calc_target_stem().with_suffix(".zip")
        target_zip = self.locs.temp / zip_name
        return target_zip

    def _calc_target_stem(self):
        target = pl.Path(self.zip_name)
        date   = self.date
        match date:
            case False:
                target_stem = target
            case True:
                now         = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
                target_stem = f"{target.stem}-{now}"
            case str():
                now         = datetime.datetime.strftime(datetime.datetime.now(), date)
                target_stem = f"{target.stem}-{now}"

        return target_stem


