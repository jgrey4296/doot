##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup

##-- end imports
# https://python-poetry.org/docs/cli/
# TODO add increment version tasks, plus update __init__.py

install      = CmdTask("poetry", "install")
wheel        = CmdTask("poetry", "build", "--format", "wheel")
requirements = CmdTask("poetry", "lock")

# TODO poetry check

