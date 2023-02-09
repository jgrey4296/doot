##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot import tasker, task_mixins

##-- end imports

def task_tags_init(locs):
    """([src]) initialise gtags """
    return {
        "basename" : "gtags::init",
        "actions"  : [ task_mixins.ActionsMixin.cmd(None, ["gtags", "-C", locs.src, "."])],
        "targets"  : [ locs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
        "clean"    : True,
    }


def task_tags(locs):
    """([src]) update tag files """
    return {
        "basename" : "gtags::update",
        "actions"  : [ task_mixins.ActionsMixin.cmd(None, ["global", "-C", locs.src, "-u" ])],
        "file_dep" : [ locs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
    }
