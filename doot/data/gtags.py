##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml, src_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports


def task_tags_init():
    """:: initalise gtags """
    return {
        "basename" : "gtags::init",
        "actions" : [ CmdAction(["gtags", "-C", src_dir, "."], shell=False)],
        "targets" : [ src_dir / "GPATH",
                      src_dir / "GRTAGS",
                      src_dir / "GTAGS" ],
        "clean"   : True,
    }


def task_tags():
    """:: update tag files """
    return {
        "basename" : "gtags::update",
        "actions"  : [ CmdAction(["global", "-C", src_dir, "-u" ], shell=False)],
        "file_dep" : [ src_dir / "GPATH",
                       src_dir / "GRTAGS",
                       src_dir / "GTAGS" ],
    }
