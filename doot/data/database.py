##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

def task_mysql2sqlite():
    """ file conversion from mysql to sqlite """
    pass


def task_database_report():
    # report database tables
    # .schema .fullschema
    # .table
    pass
