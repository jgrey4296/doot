##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot import tasker

##-- end imports

# TODO handle bib/bkmk/twit tags here too

def task_tags_init(locs):
    """([src]) initalise gtags """
    return {
        "basename" : "gtags::init",
        "actions"  : [ tasker.ActionsMixin.cmd(None, ["gtags", "-C", locs.src, "."])],
        "targets"  : [ locs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
        "clean"    : True,
    }


def task_tags(locs):
    """([src]) update tag files """
    return {
        "basename" : "gtags::update",
        "actions"  : [ tasker.ActionsMixin.cmd(None, ["global", "-C", locs.src, "-u" ])],
        "file_dep" : [ locs.src / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
    }
