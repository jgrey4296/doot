##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.files.ziptask import ZipTask

##-- end imports

# TODO target into build_dir
class EbookSplitTask:

    def __init__(self, ebook, target):
        self.create_doit_tasks = self.build
        self.ebook             = pl.Path(ebook)
        self.target            = pl.Path(target)

    def build(self):
        return {
            "actions" : [ f"ebook-convert {self.ebook} {self.target}" ],
            "targets" : [ self.target ],
        }

class EbookMakeTask:
    """
    Target a epub name,
    it will depend on a zip being made first
    """

    epub_dir = "epubs"

    def __init__(self, target):
        self.create_doit_tasks = self.build
        target_name = pl.Path(target).name
        self.zip               = (build_dir / ZipTask.zip_dir / target_name).with_suffix(".zip")
        self.target            = (build_dir / EbookMakeTask.epub_dir / target_name).with_suffix(".epub")

    def build(self):
        return {
            "actions"  : [ f"ebook-convert {self.zip} {self.target}" ],
            "targets"  : [ self.target ],
            "file_dep" : [ self.zip ],
            "task_dep" : ["_checkdir::zips", "_checkdir::epub"],
        }


def task_epub_generate_manifest():
    """
    opf, ncx
    """
    pass

##-- dir check
check_epub = CheckDir(paths=[build_dir / EbookMakeTask.epub_dir], name="epub", task_dep=["_checkdir::build"],)
##-- end dir check
