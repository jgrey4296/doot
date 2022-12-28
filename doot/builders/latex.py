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
from doot.utils import globber

##-- end imports

tex_src_dir  = doc_dir   / "tex"
tex_dir      = build_dir / "tex"
tex_temp_dir = temp_dir  / "tex"

##-- directory check
latex_check = CheckDir(paths=[tex_dir,
                              tex_temp_dir ],
                       name="tex", task_dep=["_checkdir::build"])

##-- end directory check

interaction_mode = data_toml.or_get("nonstopmode").tool.doot.tex.interaction()

class LatexMultiPass(globber.FileGlobberMulti):
    """
    Trigger both latex passes and the bibtex pass
    """

    def __init__(self):
        super().__init__("tex::build", ['.tex'], [tex_src_dir], rec=True)

    def subtask_detail(self, fpath, task):
        task.update({
            "actions"  : [],
            "file_dep" : [ tex_dir / fpath.with_suffix(".pdf").name ],
        })

class LatexFirstPass(globber.FileGlobberMulti):
    """
    First pass of running latex,
    pre-bibliography resolution
    """

    def __init__(self):
        super().__init__("tex::pass:one", [".tex"], [tex_src_dir], rec=True)

    def compile_tex(self, interaction, dependencies):
        target = pl.Path(dependencies[0]).with_suffix("")
        core_cmd = f"pdflatex -interaction={interaction} -output-directory={tex_temp_dir} {target}"
        return core_cmd

    def subtask_detail(self, fpath, task):
        first_pass_pdf = tex_dir / ("1st_pass_" + fpath.with_suffix(".pdf").name)
        task.update({
                "actions"  : [CmdAction(self.compile_tex),
                              f"cp {tex_temp_dir}/{fpath.stem}.pdf {first_pass_pdf}",
                              ],
                "task_dep" : ["_checkdir::tex"],
                "file_dep" : [ fpath ],
                "targets"  : [tex_temp_dir / fpath.with_suffix(".aux").name,
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
        })
        return task

class LatexSecondPass(globber.FileGlobberMulti):
    """
    Second pass of latex compiling,
    post-bibliography resolution
    """

    def __init__(self):
        super().__init__("_tex::pass:two", [".tex"], [tex_src_dir], rec=True)

    def subtask_detail(self, fpath, task):
        no_suffix = fpath.with_suffix("")
        task.update({"actions"  : ["pdflatex -interaction={interaction}" + f" -output-directory={tex_temp_dir} {no_suffix}",
	                               "pdflatex -interaction={interaction}" + f" -output-directory={tex_temp_dir} {no_suffix}",
                                   f"cp {tex_temp_dir}/{fpath.stem}.pdf " + "{targets}",
                                   ],
                     "task_dep" : [f"_tex::pass:bibtex:{task['name']}"],
                     "file_dep" : [ tex_temp_dir / fpath.with_suffix(".aux").name,
                                    tex_temp_dir / fpath.with_suffix(".bbl").name,
                                   ],
                     "targets"  : [
                         tex_dir / fpath.with_suffix(".pdf").name
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
                     })
        return task


class LatexCheck(globber.FileGlobberMulti):
    """
    Run a latex pass, but don't produce anything,
    just check the syntax
    """

    def __init__(self):
        super().__init__("tex::check", ['.tex'], [tex_src_dir], rec=True)

    def subtask_detail(self, fpath, task):
        no_suffix = fpath.with_suffix("")
        task.update({"file_dep" : [ path ],
                     "actions"  : ["pdflatex -draftmode -interaction={interaction}" + f" -output-directory={tex_temp_dir} {no_suffix}",],
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
                     })
        return task
class BibtexCheck(globber.FileGlobberMulti):

    def __init__(self):
        super().__init__("bibtex::check", ['.bib'], [tex_src_dir], rec=True)

    def subtask_detail(self, fpath, task):
        task.update({})
        return task

class BibtexBuildTask(globber.FileGlobberMulti):
    """
    Bibliography resolution pass
    """

    def __init__(self):
        super().__init__("_tex::pass:bibtex", [".tex"], [tex_src_dir], rec=True)

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

    def subtask_detail(self, fpath, task):
        aux_file = tex_temp_dir / fpath.with_suffix(".aux").name
        bbl_file = tex_temp_dir / fpath.with_suffix(".bbl").name
        task.update({"actions"  : [ CmdAction("ggrep {dependencies} -e \\bibdata ; :", save_out="has_bib"),
                                    CmdAction(self.amend_bib_paths(aux_file)),
                                    CmdAction(self.maybe_run) ],
                     "task_dep" : [f"tex::pass:one:{task['name']}"],
                     "file_dep" : [ tex_temp_dir / "combined.bib",
                                    aux_file ],
                     "targets"  : [ bbl_file ],
                     "clean"    : True,
                     })
        return task

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
