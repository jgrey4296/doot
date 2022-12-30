##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
import re
from functools import partial
from doit.action import CmdAction

from doot import build_dir, data_toml, temp_dir, doc_dir
from doot.files.checkdir import CheckDir, DestroyDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup
from doot.utils.toml_access import TomlAccessError
from doot.utils import globber

##-- end imports


class LatexMultiPass(globber.FileGlobberMulti):
    """
    Trigger both latex passes and the bibtex pass
    """

    def __init__(self, srcs:list[pl.Path], build:pl.Path):
        super().__init__("tex::build", ['.tex'], srcs, rec=True)
        self.build_dir = build


    def subtask_detail(self, fpath, task):
        task.update({
            "actions"  : [],
            "file_dep" : [ self.build / fpath.with_suffix(".pdf").name ],
        })

class LatexFirstPass(globber.FileGlobberMulti):
    """
    First pass of running latex,
    pre-bibliography resolution
    """

    def __init__(self, srcs:list[pl.Path], temp:pl.Path, build:pl.Path, interaction="nonstopmode"):
        super().__init__("tex::pass:one", [".tex"], srcs, rec=True)
        self.temp        = temp
        self.build       = build
        self.interaction = interaction

    def subtask_detail(self, fpath, task):
        first_pass_pdf = self.pdf_name(fpath)
        task.update({
                "task_dep" : ["_checkdir::tex"],
                "file_dep" : [ fpath ],
                "targets"  : [ self.temp / fpath.with_suffix(".aux").name,
                               first_pass_pdf,
                              ],
                "clean"    : True,
                "params" : [
                    { "name"   : "interaction",
                      "short"  : "i",
                      "type"    : str,
                      "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
                      "default" : self.interaction,
                     },
                ]
        })
        return task

    def subtask_actions(self, fpath):
        return [CmdAction(self.compile_tex, shell=False),
                partial(self.move_pdf, fpath),
                ]

    def compile_tex(self, interaction, dependencies):
        target = pl.Path(dependencies[0]).with_suffix("")
        return ["pdflatex", f"-interaction={interaction}", f"-output-directory={self.temp}", target]

    def move_pdf(self, fpath, task):
        temp_pdf = self.temp / fpath.with_suffix(".pdf").name,
        assert(temp_pdf.exists())
        target_pdf = self.pdf_name(fpath)
        temp_pdf.replace(target_pdf)

    def pdf_name(self, fpath):
        first_pass_pdf = self.build / ("1st_pass_" + fpath.with_suffix(".pdf").name)
        return first_pass_pdf

class LatexSecondPass(globber.FileGlobberMulti):
    """
    Second pass of latex compiling,
    post-bibliography resolution
    """

    def __init__(self, srcs:list[pl.Path], temp:pl.Path, build:pl.Path):
        super().__init__("_tex::pass:two", [".tex"], srcs, rec=True)
        self.temp  = temp
        self.build = build

    def subtask_detail(self, fpath, task):
        no_suffix = fpath.with_suffix("")
        task.update({"task_dep" : [f"_tex::pass:bibtex:{task['name']}"],
                     "file_dep" : [ self.temp / fpath.with_suffix(".aux").name,
                                    self.temp / fpath.with_suffix(".bbl").name,
                                   ],
                     "targets"  : [ self.build/ fpath.with_suffix(".pdf").name],
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
        build_cmd = partial(self.tex_cmd, fpath)
        return [CmdAction(build_cmd, shell=False),
	            CmdAction(build_cmd, shell=False)
                partial(self.copy_pdf, fpath)
                ],

    def tex_cmd(self, fpath, interaction, task):
        no_suffix = fpath.with_suffix("")
        return ["pdflatex", f"-interaction={interaction}", f"-output-directory={self.temp}", no_suffix]

    def move_pdf(self, fpath, targets):
        temp_pdf   = self.temp  / fpath.with_suffix(".pdf").name
        assert(temp_pdf.exists())
        target_pdf = pl.Path(targets[0])
        temp_pdf.replace(target_pdf)

    

class LatexCheck(globber.FileGlobberMulti):
    """
    Run a latex pass, but don't produce anything,
    just check the syntax
    """

    def __init__(self, srcs:list[pl.Path], temp:pl.Path):
        super().__init__("tex::check", ['.tex'], srcs, rec=True)
        self.temp = temp

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
        return [ CmdAction(partial(self.build_draft_cmd, fpath), shell=False) ]

    def build_draft_cmd(self, fpath, interaction):
        no_suffix = fpath.with_suffix("")
        return ["pdflatex", "-draftmode", f"-interaction={interaction}", f"-output-directory={self.temp}", no_suffix]

class BibtexCheck(globber.FileGlobberMulti):
    """
    TODO
    """

    def __init__(self):
        super().__init__("bibtex::check", ['.bib'], [tex_src_dir], rec=True)

    def subtask_detail(self, fpath, task):
        task.update({})
        return task

class BibtexBuildTask(globber.FileGlobberMulti):
    """
    Bibliography resolution pass
    """

    def __init__(self, srcs:list[pl.Path], temp:pl.Path, build:pl.Path):
        super().__init__("_tex::pass:bibtex", [".tex"], [tex_src_dir], rec=True)
        self.temp = temp
        self.build = build

    def subtask_detail(self, fpath, task):
        aux_file = self.temp / fpath.with_suffix(".aux").name
        bbl_file = self.temp / fpath.with_suffix(".bbl").name
        task.update({"task_dep" : [f"tex::pass:one:{task['name']}"],
                     "file_dep" : [ self.temp / "combined.bib",
                                    aux_file ],
                     "targets"  : [ bbl_file ],
                     "clean"    : True,
                     })
        return task

    def subtask_actions(self, fpath):
        aux_file = self.temp  / fpath.with_suffix(".aux").name
        bbl_file = self.temp / fpath.with_suffix(".bbl").name

        return [ CmdAction(self.grep_dependencies, shell=False, save_out="has_bib"),
                 CmdAction(self.amend_bib_paths(aux_file), shell=False),
                 CmdAction(self.maybe_run, shell=False),
                 ]

    def grep_dependencies(self, dependencies):
        return ["ggrep", "-e", "\\bibdata", *dependencies]

    def amend_bib_paths(self, aux):
        # reminder: {{ }} for escaping {'s in string.format,
        # \\{ for escaping {'s in sed
        bib_loc =  str(self.temp / "combined.bib").replace("/", "\/")
        return ["gsed", "-i.backup", "-E", "s/\\\\bibdata\\{{.+?\\}}/\\\\bibdata\\{{" + bib_loc + "\\}}/' ", aux]

    def maybe_run(self, task, dependencies, targets):
        deps = { pl.Path(x).suffix : x for x in dependencies }

        if not bool(task.values['has_bib']):
            return ["touch", *targets]

        return ["bibtex",  deps['.aux']]


class BibtexConcatenateTask:
    """
    concatenate all found bibtex files
    to produce a master file for latex's use
    """
    def __init__(self, srcs:list[pl.Path], temp:pl.Path):
        self.create_doit_tasks = self.build
        self.srcs = srcs
        self.temp = temp

    def build(self):
        # Find all bibs in each src dir
        find_actions = [ CmdAction(["find", x, "-name", "*.bib"], shell=False, save_out=str(x)) for x in self.srcs ]

        return {
            "basename" : "_tex::bib",
            "actions"  : [ *find_actions, self.concat_bibs ],
            "task_dep" : [ "_checkdir::tex" ],
            "targets"  : [ tex_temp_dir / "combined.bib" ],
            "clean"    : True,
        }

    def concat_bibs(self, targets, task):
        src_bibs : set[pl.Path] = set()
        for src in self.srcs:
            src_bibs.update(pl.Path(x) for x in task.values[str(src)].split("\n") if bool(x))

        with open(targets[0], 'w') as f:
            for bib in src_bibs:
                assert(bib.exists())
                f.write(bib.read_text() + "\n")

def task_latex_install(dep="tex.dependencies"):
    """
    install dependencies for the latex document
    """

    def build_install_instr(task):
        dep_lines = {x for x in pl.Path(dep).read_text().split("\n") if bool(x)}
        return ["tlmgr", "--usermode",  "install", *dep_lines]


    if not pl.Path(dep).exists():
        return None

    return {
        "basename" : "tex::install",
        "actions"  : [CmdAction(build_install_instr, shell=False)],
        "file_dep" : [ dep ],

    }

def task_latex_requirements(reqf="tex.requirements"):
    """
    create a requirements
    """
    def write_reqs(task):
        pl.Path(reqf).write_text(task.values['reqs'])
    
    return {
        "basename" : "tex::requirements",
        "actions" : [ CmdAction(["tlmgr", "--usermode", "list", "--only-installed", "--data", "name"], shell=False, save_out="reqs"),
                      write_reqs,
                     ],
        "targets" : [ reqf ],
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
    package_re = re.compile("^i (.+?):.+?$")

    def build_install_cmd(task):
        packages = [package_re.match(x)[1] for x in task.values['installed'].split("\n") if package_re.match(x)]
        return ["tlmgr", "install", "--reinstall", *packages]
    
    return {
        "basename" : "tex::rebuild",
        "actions" : [ CmdAction(["fmtutil",  "--all"], shell=False),
                      CmdAction(["tlmgr",  "list", "--only-installed"], shell=False, save_out="installed"),
                      CmdAction(build_install_cmd, shell=False)
        ],
    }


def build_latex_check(tex_build:pl.Path, tex_temp:pl.path):
    CheckDir(paths=[tex_build,
                    tex_temp],
             name="tex", task_dep=["_checkdir::build"])
