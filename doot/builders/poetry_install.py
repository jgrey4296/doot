##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports
# https://python-poetry.org/docs/cli/
# TODO add increment version tasks, plus update __init__.py

poetry_install      = JGCmdTask("poetry", "install")
poetry_wheel        = JGCmdTask("poetry", "build", "--format", "wheel")
poetry_requirements = JGCmdTask("poetry", "lock")

# TODO poetry check
