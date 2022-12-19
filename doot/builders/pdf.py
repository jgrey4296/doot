##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup

##-- end imports


class SplitPDFTask:

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        pass


class CombinePDFTask:

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        pass
