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

    def subtask_detail(self, fpath, task):
        first_pass_pdf = self.pdf_name(fpath)
        task.update({
                "task_dep" : ["_checkdir::tex"],
                "file_dep" : [ fpath ],
                "targets"  : [ tex_temp_dir / fpath.with_suffix(".aux").name,
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

    def subtask_actions(self, fpath):
        return [CmdAction(self.compile_tex, shell=False),
                CmdAction(["cp",
                           tex_temp_dir / fpath.with_suffix(".pdf").name,
                           self.pdf_name(fpath) ],
                          shell=False),
                ]

    def pdf_name(self, fpath):
        first_pass_pdf = tex_dir / ("1st_pass_" + fpath.with_suffix(".pdf").name)
        return first_pass_pdf

    def compile_tex(self, interaction, dependencies):
        target = pl.Path(dependencies[0]).with_suffix("")
        core_cmd = ["pdflatex", "-interaction={interaction}", "-output-directory={tex_temp_dir}", target]
        return core_cmd

class LatexSecondPass(globber.FileGlobberMulti):
    """
    Second pass of latex compiling,
    post-bibliography resolution
    """

    def __init__(self):
        super().__init__("_tex::pass:two", [".tex"], [tex_src_dir], rec=True)

    def subtask_detail(self, fpath, task):
        no_suffix = fpath.with_suffix("")
        task.update({"task_dep" : [f"_tex::pass:bibtex:{task['name']}"],
                     "file_dep" : [ tex_temp_dir / fpath.with_suffix(".aux").name,
                                    tex_temp_dir / fpath.with_suffix(".bbl").name,
                                   ],
                     "targets"  : [tex_dir / fpath.with_suffix(".pdf").name],
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

    def subtask_actions(self, fpath):
        no_suffix = fpath.with_suffix("")
        return [CmdAction(["pdflatex", "-interaction={interaction}", f"-output-directory={tex_temp_dir}", no_suffix], shell=False),
	            CmdAction(["pdflatex", "-interaction={interaction}", f"-output-directory={tex_temp_dir}", no_suffix], shell=False)
                CmdAction(["cp", tex_temp_dir / fpath.with_suffix(".pdf").name, "{targets}"], shell=False),
                ],


class LatexCheck(globber.FileGlobberMulti):
    """
    Run a latex pass, but don't produce anything,
    just check the syntax
    """

    def __init__(self):
        super().__init__("tex::check", ['.tex'], [tex_src_dir], rec=True)

    def subtask_detail(self, fpath, task):
        task.update({"file_dep" : [ path ],
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

    def subtask_actions(self, fpath):
        no_suffix = fpath.with_suffix("")
        return [CmdAction(["pdflatex", "-draftmode", "-interaction={interaction}", f"-output-directory={tex_temp_dir}", no_suffix], shell=False)],

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

    def subtask_detail(self, fpath, task):
        aux_file = tex_temp_dir / fpath.with_suffix(".aux").name
        bbl_file = tex_temp_dir / fpath.with_suffix(".bbl").name
        task.update({"task_dep" : [f"tex::pass:one:{task['name']}"],
                     "file_dep" : [ tex_temp_dir / "combined.bib",
                                    aux_file ],
                     "targets"  : [ bbl_file ],
                     "clean"    : True,
                     })
        return task

    def subtask_actions(self, fpath):
        aux_file = tex_temp_dir / fpath.with_suffix(".aux").name
        bbl_file = tex_temp_dir / fpath.with_suffix(".bbl").name

        return [ CmdAction(["ggrep", "{dependencies}", "-e", "\\bibdata", ";",  ":"], shell=False, save_out="has_bib"),
                 CmdAction(self.amend_bib_paths(aux_file), shell=False),
                 CmdAction(self.maybe_run, shell=False),
                 ]

    def amend_bib_paths(self, aux):
        # reminder: {{ }} for escaping {'s in string.format,
        # \\{ for escaping {'s in sed
        bib_loc =  str(tex_temp_dir / "combined.bib").replace("/", "\/")
        cmd = ["gsed", "-i.backup", "-E", "s/\\\\bibdata\\{{.+?\\}}/\\\\bibdata\\{{" + str(bib_loc) + "\\}}/' ", str(aux)]
        return cmd

    def maybe_run(self, task, dependencies):
        deps = { pl.Path(x).suffix : x for x in dependencies }

        if not bool(task.values['has_bib']):
            return "touch {targets}"

        return ["bibtex",  deps['.aux']]


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
                # TODO could save out, then cat in separate action
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
