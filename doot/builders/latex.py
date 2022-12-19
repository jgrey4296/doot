##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir, DestroyDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup

##-- end imports

latex_dir = build_dir / "latex"
temp_dir  = build_dir / "temp"
##-- directory setup/teardown
check_build       = CheckDir(paths=[latex_dir], name="latex", task_dep=["_checkdir::build"])
check_temp        = CheckDir(paths=[ temp_dir ], name="latex.setup", task_dep=["_checkdir::build"])
teardown_teardown = DestroyDir(paths=[ temp_dir ], name="latex.teardown")

##-- end directory setup/teardown

class LatexBuildTask:
    """
    Compile a latex file,
    """


    def __init__(self, tex=None):
        self.create_doit_tasks = self.build
        self.src      = pl.Path(tex).stem
        self.target   = temp_dir / self.src.with_suffix(".pdf").name

    def build(self):
        return {
            "basename" : "latex::build",
            "actions"  : [
	            f"pdflatex -output-directory={temp_dir} {self.src}",
            ],
            "task_dep" : ["_checkdir::latex", "_checkdir::latex.setup"],
            "file_dep" : [ self.src.with_suffix(".tex") ],
            "targets"  : [ self.target ],
            "clean"    : True,
        }

class BibtexBuildTask:
    """ run bibtex on a compiled latex file to insert references """

    def __init__(self, tex=None, bib=None, **kwargs):
        self.create_doit_tasks = self.build
        self.tex      = pl.Path(tex)
        self.bib      = pl.Path(bib)
        self.src      = temp_dir / self.tex.with_suffix(".aux").name
        self.target   = self.src.with_suffix(".bbl").name


    def build(self):
        return {
            "basename" : "bibtex::build",
            "actions"  : [ f"bibtex {self.src}" ],
            "task_dep" : ["_checkdir::latex.setup"],
            "file_dep" : [ self.tex, self.bib ],
            "targets"  : [ self.target ],
            "clean"    : True,
        }

class BibtexConcatenateTask:
    """ concatenate all found bibtex files to produce a master file for building with  """
    def __init__(self, globs=None, target=None):
        self.create_doit_tasks = self.build
        self.globs    = globs or []
        self.target   = (temp_dir / target).with_suffix(".bib")

    def glob_bibs(self):
        found = {}
        for glob in self.globs:
            found += pl.Path(".").glob(glob)

        return found

    def build(self):
        all_bibs = self.glob_bibs()

        return {
            "basename" : "bibtex::concat",
            "actions"  : [
	            f"cat {all_bibs} > {self.target} ",
                ],
            "task_dep" : ["_checkdir::latex", "_checkdir::latex.setup"],
            "file_dep" : [  ],
            "targets"  : [ self.target ],
            "clean"    : True,
        }


def task_latex_install():
    """
    install dependencies for the latex document
    """

    return {
        "basename" : "latex::install",
        "actions"  : ["tlmgr --usermode install `cat tex.dependencies`"],
        "file_dep" : ["tex.requirements"],

    }

def task_latex_requirements():
    """
    create a requirements
    """
    return {
        "basename" : "latex::requirements",
        "actions" : [ "tlmgr --usermode list --only-installed --data name > tex.requirements"],
        "targets" : [ "tex.requirements" ],
    }

def task_latex_docs():
    """ run texdoc  """
    return {
        "basename" : "latex::docs",
        "actions" : ["texdoc {package}"],
        "params" : [ { "name" : "package",
                       "long" : "package",
                       "short" : "p",
                       "type" : str,
                       "default" : "--help",
                       }
                    ],
    }


def task_latex_rebuild():
    """ rebuild tex formats and metafonts, for handling outdated l3 layer errors """
    return {
        "basename" : "latex::rebuild",
        "actions" : [ "fmtutil --all",
        "tlmgr install --reinstall $(tlmgr list --only-installed | sed -E 's/i (.*):.*$/\1/')",
        ],
    }
