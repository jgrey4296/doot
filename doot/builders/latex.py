##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

from doot import build_dir, data_toml, temp_dir, doc_dir
from doot.files.checkdir import CheckDir, DestroyDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup
from doot.utils.toml_access import TomlAccessError

##-- end imports

tex_src_dir  = doc_dir   / "tex"
tex_dir      = build_dir / "tex"
tex_temp_dir = temp_dir  / "tex"

##-- directory check
latex_check = CheckDir(paths=[tex_dir,
                              tex_temp_dir ],
                       name="tex", task_dep=["_checkdir::build"])

##-- end directory check

interaction_mode = data_toml.or_get("nonstopmode").tool.doot.tex.interaction

class LatexMultiPass:
    """
    Trigger both latex passes and the bibtex pass
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in tex_src_dir.rglob("*.tex"):
            yield {
                "basename" : "tex::build",
                "name"     : path.stem,
                "actions"  : [],
                "file_dep" : [ tex_dir / path.with_suffix(".pdf").name ],
            }

class LatexFirstPass:
    """
    First pass of running latex,
    pre-bibliography resolution
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def compile_tex(self, interaction, dependencies):
        target = pl.Path(dependencies[0]).with_suffix("")
        core_cmd = f"pdflatex -interaction={interaction} -output-directory={tex_temp_dir} {target}"
        return core_cmd

    def build(self):
        for path in tex_src_dir.rglob("*.tex"):
            first_pass_pdf = tex_dir / ("1st_pass_" + path.with_suffix(".pdf").name)
            yield {
                "basename" : "tex::pass:one",
                "name"     : path.stem,
                "actions"  : [
                    CmdAction(self.compile_tex),
                    f"cp {tex_temp_dir}/{path.stem}.pdf {first_pass_pdf}",
                ],
                "task_dep" : ["_checkdir::tex"],
                "file_dep" : [ path ],
                "targets"  : [
                    tex_temp_dir / path.with_suffix(".aux").name,
                    first_pass_pdf,
                ],
                "clean"    : True,
                "params" : [
                    { "name"   : "interaction",
                      "short"  : "i",
                      "type"    : str,
                      "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
                      "default" : interaction_mode,
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
        for path in tex_src_dir.rglob("*.tex"):
            no_suffix = path.with_suffix("")
            yield {
                "basename" : "_tex::pass:two",
                "name"     : path.stem,
                "actions"  : [
	                "pdflatex -interaction={interaction}" + f" -output-directory={tex_temp_dir} {no_suffix}",
	                "pdflatex -interaction={interaction}" + f" -output-directory={tex_temp_dir} {no_suffix}",
                    f"cp {tex_temp_dir}/{path.stem}.pdf " + "{targets}",
                ],
                "task_dep" : [f"_tex::pass:bibtex:{path.stem}"],
                "file_dep" : [ tex_temp_dir / path.with_suffix(".aux").name,
                               tex_temp_dir / path.with_suffix(".bbl").name,
                              ],
                "targets"  : [
                    tex_dir / path.with_suffix(".pdf").name
                ],
                "clean"    : True,
                "params" : [
                    { "name"   : "interaction",
                     "short"  : "i",
                     "type"    : str,
                     "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
                     "default" : "nonstopmode",
                    },
                   ],
                "uptodate": [False],
            }


class LatexCheck:
    """
    Run a latex pass, but don't produce anything,
    just check the syntax
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in tex_src_dir.rglob("*.tex"):
            no_suffix = path.with_suffix("")
            yield {
                "basename" : "tex::check",
                "name"     : path.stem,
                "actions"  : [
                    "pdflatex -draftmode -interaction={interaction}" + f" -output-directory={tex_temp_dir} {no_suffix}",
                ],
                "file_dep" : [ path ],
                "task_dep" : [ "_checkdir::tex" ],
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
        return f"find {tex_src_dir} -name '*.tex' -print0 | xargs -0 grep -l -E -e '\\\bibliography' > {tex_temp_dir}/todos"

    def amend_bib_paths(self, aux):
        # reminder: {{ }} for escaping {'s in string.format,
        # \\{ for escaping {'s in sed
        bib_loc =  str(tex_temp_dir / "combined.bib").replace("/", "\/")
        cmd = "gsed -i.backup -E 's/\\\\bibdata\\{{.+?\\}}/\\\\bibdata\\{{" + str(bib_loc) + "\\}}/' " + str(aux)
        return cmd

    def maybe_run(self, task, dependencies):
        deps = { pl.Path(x).suffix : x for x in dependencies }

        if not bool(task.values['has_bib']):
            return "touch {targets}"

        return f"bibtex {deps['.aux']}"

    def build(self):
        for path in tex_src_dir.rglob("*.tex"):
            aux_file = tex_temp_dir / path.with_suffix(".aux").name
            bbl_file = tex_temp_dir / path.with_suffix(".bbl").name
            yield {
                "basename" : "_tex::pass:bibtex",
                "name"     : path.stem,
                "actions"  : [ CmdAction("ggrep {dependencies} -e \\bibdata ; :", save_out="has_bib"),
                               CmdAction(self.amend_bib_paths(aux_file)),
                               CmdAction(self.maybe_run) ],
                "task_dep" : [f"tex::pass:one:{path.stem}"],
                "file_dep" : [ tex_temp_dir / "combined.bib",
                               aux_file ],
                "targets"  : [ bbl_file ],
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
            "basename" : "_tex::bib",
            "actions"  : [
                # Concatenate the bibliography
	            CmdAction(f"find {tex_src_dir} -name '*.bib' -print0 | xargs -0 cat " + " > {targets}"),
                # copy any bib styles
                # CmdAction(f"find {tex_src_dir} -name '*.bst' -print0 | xargs -0 -I %s cp %s {tex_temp_dir}"),
            ],
            "task_dep" : ["_checkdir::tex"],
            "targets"  : [ tex_temp_dir / "combined.bib" ],
            "clean"    : True,
        }


def task_latex_install():
    """
    install dependencies for the latex document
    """

    return {
        "basename" : "tex::install",
        "actions"  : ["tlmgr --usermode install `cat tex.dependencies`"],
        "file_dep" : ["tex.requirements"],

    }

def task_latex_requirements():
    """
    create a requirements
    """
    return {
        "basename" : "tex::requirements",
        "actions" : [ "tlmgr --usermode list --only-installed --data name > tex.requirements"],
        "targets" : [ "tex.requirements" ],
    }

def task_latex_docs():
    """ run texdoc  """
    return {
        "basename" : "tex::docs",
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
        "basename" : "tex::rebuild",
        "actions" : [ "fmtutil --all",
        "tlmgr install --reinstall $(tlmgr list --only-installed | sed -E 's/i (.*):.*$/\1/')",
        ],
    }
