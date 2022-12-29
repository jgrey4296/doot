
##-- imports
from __future__ import annotations

import datetime
import logging as logmod
import pathlib as pl
import zipfile

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

zip_dir = build_dir / "zips"

##-- dir check
check_zips = CheckDir(paths=[zip_dir], name="zips", task_dep=["_checkdir::build"],)
##-- end dir check

__all__ = [
        "ZipTask"
]

class ZipTask:
    """
    Automate creation of archive zipfiles
    will be named `zip::{name/default}`
    specify `paths` and/or `globs`,
    set `data` to True or a datetime.strftime format to customize naming
    (time is based on task creation time, not task execution time)

    TODO timeout={int} for rebuilding if target zip is hours? days? too old?
    TODO add filter_fn
    """

    def __init__(self, *, target=None, target_dir=zip_dir, paths=None, globs=None, base="zip::default", date=False, **kwargs):
        self.create_doit_tasks        = self.build
        self.date     : bool | str    = date
        self.target_dir               = target_dir
        self.file_dep : list[pl.Path] = [pl.Path(x) for x in paths or []]
        self.globs    : list[str]     = globs or []
        self.kwargs                   = kwargs
        self.default_spec             = {"basename" : base,
                                         "uptodate" : [False],
                                         }

        if target is not None:
            self.target = pl.Path(target)
            assert(self.target.suffix == ".zip")

    def formatted_target(self, target):
        target      = pl.Path(target)
        target_stem = target.stem
        match self.date:
            case False:
                pass
            case True:
                now         = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
                target_stem = f"{target.stem}-{now}"
            case str():
                now         = datetime.datetime.strftime(datetime.datetime.now(), date)
                target_stem = f"{target.stem}-{now}"

        return target.with_stem(target_stem)


    def action_zip_create(self, task):
        if task.meta['zip'].exists():
            return

        now = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
        record_str = f"Zip File created at {now} for doot task: {task.name}"

        with zipfile.ZipFile(task.meta['zip'], 'w') as targ:
            targ.writestr(".taskrecord", record_str)

    def action_zip_add_paths(self, task, dependencies):
        assert(all(pl.Path(x).exists() for x in dependencies))
        with zipfile.ZipFile(task.meta['zip'], 'a') as targ:
            for dep in dependencies:
                targ.write(str(dep))

    def action_zip_globs(self, task):
        logging.debug(f"Globbing: {task.meta['globs']}")
        cwd = pl.Path(".")
        with zipfile.ZipFile(task.meta['zip'], 'a') as targ:
            for glob in task.meta['globs']:
                result = list(cwd.glob(glob))
                print(f"Globbed: {cwd}[{glob}] : {len(result)}")
                for dep in result:
                    targ.write(dep)


    def clean_zips(self, task):
        zip_base = task.meta['zip'].parent
        print(f"Cleaning {zip_base}/{task.meta['stem']}*.zip")
        for zipf in zip_base.glob(f"{task.meta['stem']}*.zip"):
            zipf.unlink()
        task.meta['zip'].unlink(missing_ok=True)

    
    def build(self, *, name=None, target=None, file_dep=None, globs=None) -> dict:
        target      = self.target_dir / (target or self.target)
        target_stem = target.stem
        task_desc   = self.default_spec.copy()
        formatted   = self.formatted_target(target)

        file_dep = file_dep or self.file_dep
        globs    = globs or self.globs

        task_desc.update(self.kwargs)
        task_desc.update({
            "actions"  : [ self.action_zip_create, self.action_zip_add_paths, self.action_zip_globs],
            "clean"    : [self.clean_zips],
            "file_dep" : file_dep,
            "task_dep" : ["_checkdir::zips"],
            "meta"     : { "stem"  : target_stem,
                           "globs" : globs,
                           "zip"   : target,
                           },
        })
        if name is not None:
            task_desc.update({
                "name" : name
                })
        return task_desc


