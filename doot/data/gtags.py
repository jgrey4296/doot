##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports


def task_tags_init():
    """:: initalise gtags """
    return {
        "actions" : [ f"gtags -C {src_dir} ." ],
        "targets" : [ src_dir / "GPATH",
                      src_dir / "GRTAGS",
                      src_dir / "GTAGS" ],
        "basename" : "_tags_init",
    }


def task_tags():
    """:: update tag files """
    return {
        "actions"  : [],
        "file_dep" : [ src_dir / "GPATH",
                       src_dir / "GRTAGS",
                       src_dir / "GTAGS" ],
    }
