##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask

##-- end imports


def task_tags_init(dirs):
    """([src]) initalise gtags """
    return {
        "basename" : "gtags::init",
        "actions"  : [ CmdAction(["gtags", "-C", dirs.src, "."], shell=False)],
        "targets"  : [ dirs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
        "clean"    : True,
    }


def task_tags(dirs):
    """([src]) update tag files """
    return {
        "basename" : "gtags::update",
        "actions"  : [ CmdAction(["global", "-C", dirs.src, "-u" ], shell=False)],
        "file_dep" : [ dirs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
    }
