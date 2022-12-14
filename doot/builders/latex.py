##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir, DestroyDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup

##-- end imports


# def task_latex_full_build():
#     yield firstpass
#     yield bibtexpass
#     yield secondpass
#     yield finalpass
# "task_dep" : ["checkdir::latex"],
# "setup"    : ["checkdir::latex.setup"],


class LatexBuildTask:

    latex_dir = "latex"

    def __init__(self, tex=None, **kwargs):
        self.src      = pl.Path(tex).stem

        self.temp_dir = build_dir / "temp"
        self.target   = temp_dir / self.src.with_suffix(".pdf").name



    def build(self):
        return {
            "actions"  : [
	            f"pdflatex -output-directory={temp_dir} {self.src}",
                ],
            "task_dep" : ["checkdir::latex", "checkdir::latex.setup"],
            "file_dep" : [ self.src.with_suffix(".tex") ],
            "targets"  : [ self.target ],
            "clean"    : True,
        }

class BibtexBuildTask:

    def __init__(self, tex=None, bib=None, **kwargs):
        self.tex      = pl.Path(tex)
        self.bib      = pl.Path(bib)
        self.temp_dir = build_dir / "temp"
        self.src      = temp_dir / self.tex.with_suffix(".aux").name
        self.target   = self.src.with_suffix(".bbl").name


    def build(self):
        return {
            "actions"  : [ f"bibtex {self.src}" ],
            "task_dep" : ["checkdir::latex.setup"],
            "file_dep" : [ self.tex, self.bib ],
            "targets"  : [ self.target ],
            "clean"    : True,
        }

class BibtexCompileTask:
    def __init__(self, globs=None, target=None, **kwargs):
        self.globs    = globs or []
        self.temp_dir = build_dir / "temp"
        self.target   = (self.temp_dir / target).with_suffix(".bib")

    def glob_bibs(self):
        return {}

    def cat_bibs(self):
        return {}

    def build(self):
        return {
            "actions"  : [
	            f"cat {self.globs} > {self.target} ",
                ],
            "task_dep" : ["checkdir::latex", "checkdir::latex.setup"],
            "file_dep" : [  ],
            "targets"  : [ self.target ],
            "clean"    : True,
        }


def task_latex_install_dependencies():
    pass

def task_latex_docs():
    pass

##-- directory setup/teardown
output_dir        = CheckDir(paths=[build_dir / LatexBuildTask.latex_dir], name="latex")
setup_temp        = CheckDir(paths=[build_dir / "temp"], name="latex.setup")
teardown_teardown = DestroyDir(paths=[build_dir / "temp"], name="latex.teardown")

##-- end directory setup/teardown
