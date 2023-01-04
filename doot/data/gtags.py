##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask

##-- end imports


def task_tags_init(dirs):
    """:: initalise gtags """
    return {
        "basename" : "gtags::init",
        "actions" : [ CmdAction(["gtags", "-C", dirs.src, "."], shell=False)],
        "targets" : [ dirs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
        "clean"   : True,
    }


def task_tags(dirs):
    """:: update tag files """
    return {
        "basename"  : "gtags::update",
        "actions"   : [ CmdAction(["global", "-C", dirs.src, "-u" ], shell=False)],
        "file_deps" : [ dirs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
    }
