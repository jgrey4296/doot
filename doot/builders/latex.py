##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir, DestroyDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup

##-- end imports

src_dir   = pl.Path("docs") / "tex"
latex_dir = build_dir / "latex"
temp_dir  = latex_dir / "temp"

##-- directory check
latex_check = CheckDir(paths=[latex_dir,
                              temp_dir ],
                       name="latex", task_dep=["_checkdir::build"])

##-- end directory check

class LatexMultiPass:
    """
    Trigger both latex passes and the bibtex pass
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in src_dir.rglob("*.tex"):
            yield {
                "basename" : "latex::build",
                "name"     : path.stem,
                "actions"  : [],
                "file_dep" : [ latex_dir / path.with_suffix(".pdf").name ],
            }

class LatexFirstPass:
    """
    First pass of running latex,
    pre-bibliography resolution
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in src_dir.rglob("*.tex"):
            no_suffix = path.with_suffix("")
            first_pass_pdf = latex_dir / ("1st_pass_" + path.with_suffix(".pdf").name)
            yield {
                "basename" : "latex::pass:one",
                "name"     : path.stem,
                "actions"  : [
	                "pdflatex -interaction={interaction}" + f" -output-directory={temp_dir} {no_suffix}",
                    f"cp {temp_dir}/{path.stem}.pdf {first_pass_pdf}",
                ],
                "task_dep" : ["_checkdir::latex"],
                "file_dep" : [ path ],
                "targets"  : [
                    temp_dir / path.with_suffix(".aux").name,
                    first_pass_pdf,
                ],
                "clean"    : True,
                "params" : [
                    { "name"   : "interaction",
                     "short"  : "i",
                     "type"    : str,
                     "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
                     "default" : "nonstopmode",
                    },
                   ]
            }
class LatexSecondPass:
    """
    Second pass of latex compiling,
    post-bibliography resolution
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in src_dir.rglob("*.tex"):
            no_suffix = path.with_suffix("")
            yield {
                "basename" : "latex::pass:two",
                "name"     : path.stem,
                "actions"  : [
	                "pdflatex -interaction={interaction}" + f" -output-directory={temp_dir} {no_suffix}",
                    f"cp {temp_dir}/{path.stem}.pdf " + "{targets}",
                ],
                "task_dep" : [f"latex::pass:bibtex:{path.stem}"],
                "file_dep" : [ temp_dir / path.with_suffix(".aux").name,
                               temp_dir / path.with_suffix(".bbl").name,
                              ],
                "targets"  : [
                    latex_dir / path.with_suffix(".pdf").name
                ],
                "clean"    : True,
                "params" : [
                    { "name"   : "interaction",
                     "short"  : "i",
                     "type"    : str,
                     "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
                     "default" : "nonstopmode",
                    },
                   ]
            }


class LatexCheck:
    """
    Run a latex pass, but don't produce anything,
    just check the syntax
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in src_dir.rglob("*.tex"):
            no_suffix = path.with_suffix("")
            yield {
                "basename" : "latex::check",
                "name"     : path.stem,
                "actions"  : [
                    "pdflatex -draftmode -interaction={interaction}" + f" -output-directory={temp_dir} {no_suffix}",
                ],
                "file_dep" : [ path ],
                "task_dep" : [ "_checkdir::latex" ],
                "uptodate" : [False],
                "params" : [
                    { "name"   : "interaction",
                     "short"  : "i",
                     "type"    : str,
                     "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
                     "default" : "nonstopmode",
                    },
                   ]

            }
class BibtexBuildTask:
    """
    Bibliography resolution pass
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def texs_with_bibs(self):
        return f"find {src_dir} -name '*.tex' -print0 | xargs -0 grep -l -E -e '\\\bibliography' > {temp_dir}/todos"


    def build(self):
        for path in src_dir.rglob("*.tex"):
            yield {
                "basename" : "latex::pass:bibtex",
                "name"     : path.stem,
                "actions"  : [ f"bibtex {temp_dir}/{path.stem}.aux" ],
                "task_dep" : [f"latex::pass:one:{path.stem}"],
                "file_dep" : [ latex_dir / "combined.bib",
                               temp_dir / path.with_suffix(".aux").name ],
                "targets"  : [ temp_dir / path.with_suffix(".bbl").name ],
                "clean"    : True,
            }

class BibtexConcatenateTask:
    """
    concatenate all found bibtex files
    to produce a master file for latex's use
    """
    def __init__(self, globs=None, target=None):
        self.create_doit_tasks = self.build

    def build(self):
        return {
            "basename" : "bibtex::concat",
            "actions"  : [
	            CmdAction(f"find {src_dir} -name '*.bib' -print0 | xargs -0 cat " + " > {targets}")
            ],
            "task_dep" : ["_checkdir::latex"],
            "targets"  : [ latex_dir / "combined.bib" ],
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
