##-- imports
from __future__ import annotations

import pathlib as pl
import zipfile
import datetime

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

zip_dir = build_dir / "zips"

##-- dir check
check_zips = CheckDir(paths=[zip_dir], name="zips", task_dep=["_checkdir::build"],)
##-- end dir check

class ZipTask:
    """
    Automate creation of archive zipfiles
    will be named `zip::{name/default}`
    specify `paths` and/or `globs`,
    set `data` to True or a datetime.strftime format to customize naming
    (time is based on task creation time, not task execution time)

    TODO timeout={int} for rebuilding if target zip is hours? days? too old?
    """

    def __init__(self, target, *, target_dir=zip_dir, paths=None, globs=None, base="zip::default", date=False, **kwargs):
        target = pl.Path(target)
        assert(target.suffix == ".zip")
        self.create_doit_tasks = self.build
        self.date              = date
        self.target_dir        = target_dir
        match date:
            case False:
                self.target : pl.Path = target
            case True:
                now                   = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
                dated_target          = f"{target.stem}-{now}.zip"
                self.target : pl.Path = dated_target
            case str():
                now                   = datetime.datetime.strftime(datetime.datetime.now(), date)
                dated_target          = f"{target.stem}-{now}.zip"
                self.target : pl.Path = dated_target


        self.file_dep : list[pl.Path] = [pl.Path(x) for x in paths or []]
        self.globs : list[str]        = globs or []
        self.kwargs                   = kwargs
        self.default_spec             = {"basename": base }

    def action_zip_create(self):
        assert(all(x.exists() for x in self.file_dep))
        with zipfile.ZipFile(self.target_dir / self.target, 'w') as targ:
            for dep in self.file_dep:
                targ.write(str(dep))

    def action_zip_globs(self):
        print(f"Globbing: {self.globs}")
        cwd = pl.Path(".")
        with zipfile.ZipFile(self.target_dir / self.target, 'a') as targ:
            for glob in self.globs:
                result = list(cwd.glob(glob))
                print(f"Globbed: {cwd}[{glob}] : {len(result)}")
                for dep in result:
                    targ.write(dep)

    # def uptodate(self):
    #     return all([x.exists() for x in self.args])

    def clean_zips(self):
        zip_base = self.target_dir
        print(f"Cleaning {zip_base}/{self.target.stem}*.zip")
        for zipf in zip_base.glob(f"{self.target.stem}*.zip"):
            zipf.unlink()

    
    def build(self) -> dict:
        task_desc = self.default_spec.copy()
        task_desc.update(self.kwargs)
        task_desc.update({
            "actions"  : [ self.action_zip_create, self.action_zip_globs],
            "targets"  : [ self.target ],
            "uptodate" : [False],
            "clean"    : [self.clean_zips],
            "task_dep" : ["_checkdir::zips"],
        })
        return task_desc


