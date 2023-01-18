##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot import tasker

##-- end imports

# TODO handle bib/bkmk/twit tags here too

def task_tags_init(dirs):
    """([src]) initalise gtags """
    return {
        "basename" : "gtags::init",
        "actions"  : [ tasker.ActionsMixin.cmd(None, ["gtags", "-C", dirs.src, "."])],
        "targets"  : [ dirs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
        "clean"    : True,
    }


def task_tags(dirs):
    """([src]) update tag files """
    return {
        "basename" : "gtags::update",
        "actions"  : [ tasker.ActionsMixin.cmd(None, ["global", "-C", dirs.src, "-u" ])],
        "file_dep" : [ dirs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
    }
