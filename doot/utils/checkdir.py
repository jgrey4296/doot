##-- imports
from __future__ import annotations
import pathlib as pl
import shutil
from typing import ClassVar

from doot.utils.clean_dirs import clean_target_dirs
from doot.utils.task_group import TaskGroup
##-- end imports

from doot.utils.tasker import DootTasker

class CheckDir:
    """ Task for checking directories exist,
    making them if they don't
    """
    _all_check_groups : ClassVar[dict[str:CheckDir]] = {}

    _checker_name = "_locs::check"
    @staticmethod
    def gen_check_tasks():
        return TaskGroup(CheckDir._checker_name,
                         *CheckDir._all_check_groups.values(),
                         as_creator=True)


    @staticmethod
    def register(dirs:DootLocData=None):
        checker = CheckDir(dirs._postfix, dirs)
        CheckDir._all_check_groups[checker.base] = checker
        return f"{CheckDir._checker_name}:{checker.base}"

    def __init__(self, name="default", dirs=None, private=True):
        self.base = name
        self.dirs = dirs

    def is_current(self):
        return all([y.exists() for x,y in self.dirs])

    def _build_task(self) -> dict:
        task = {
            "name"      : self.base,
            "actions"   : [ self.mkdir ],
            "clean"     : [ clean_target_dirs ],
            "uptodate"  : [self.is_current],
            "verbosity" : 2,
        }
        return task

    def mkdir(self):
        for _,x in self.dirs:
            try:
                x.mkdir(parents=True)
                print("Built Missing Location: ", x)
            except FileExistsError:
                pass


class DestroyDir(DootTasker):
    """ Task that destroys a directory. ie: working directories """

    def __init__(self, name="default", dirs=None, targets=None, prefix="locs::destroy", private=True):
        full_name = f"{'__' if private else ''}{base}.{name}"
        super().__init__(name, dirs)
        self.targets      = [pl.Path(x) for x in targets or [] ]

    def is_current(self):
        return all([x.exists() for x in self.args])

    def _build_task(self, task):
        task.update({
            "actions"  : [ self.destroy_deps ],
            "file_dep" : self.paths,
            "uptodate" : [ self.uptodate ],
        })
        return task

    def destroy_deps(task, dryrun):
        """ Clean targets, including non-empty directories
        Add to a tasks 'clean' dict value
        """
        for target_s in sorted(task.file_dep, reverse=True):
            try:
                target = pl.Path(target_s)
                if dryrun:
                    print("%s - dryrun removing '%s'" % (task.name, target))
                    continue

                print("%s - removing '%s'" % (task.name, target))
                if target.is_file():
                    target.remove()
                elif target.is_dir():
                    shutil.rmtree(str(target))
            except OSError as err:
                print(err)
