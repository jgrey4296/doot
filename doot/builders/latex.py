##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
import re
import fileinput
from functools import partial
from doit.action import CmdAction

from doot import data_toml
from doot.files.checkdir import CheckDir, DestroyDir
from doot.utils.cmdtask import CmdTask
from doot.utils.task_group import TaskGroup
from doot.utils.toml_access import TomlAccessError
from doot.utils import globber
from doot.utils.tasker import DootTasker
from doot.utils.general import ForceCmd

##-- end imports

interaction_mode = data_toml.or_get("nonstopmode").tool.doot.tex.interaction()

class LatexMultiPass(globber.FileGlobberMulti):
    """
    Trigger both latex passes and the bibtex pass
    """

    def __init__(self, dirs:DootDirs, roots):
        super().__init__("tex::build", dirs, roots, exts=['.tex'], rec=True)


    def subtask_detail(self, fpath, task):
        task.update({
            "actions"  : [],
            "file_dep" : [ self.dirs.build / fpath.with_suffix(".pdf").name],
        })
        return task

class LatexFirstPass(globber.FileGlobberMulti):
    """
    First pass of running latex,
    pre-bibliography resolution
    """

    def __init__(self, dirs:DootDirs, roots:list[pl.Path], interaction=interaction_mode):
        super().__init__("tex::pass:one", dirs, roots, exts=[".tex"], rec=True)
        self.interaction = interaction

    def subtask_detail(self, fpath, task):
        first_pass_pdf = self.pdf_name(fpath)
        task.update({
                "task_dep" : ["_checkdir::tex"],
                "file_dep" : [ fpath ],
                "targets"  : [ self.dirs.temp / fpath.with_suffix(".aux").name,
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
        return ["pdflatex", f"-interaction={interaction}", f"-output-directory={self.dirs.temp}", target]

    def move_pdf(self, fpath, task):
        temp_pdf = self.dirs.temp / fpath.with_suffix(".pdf").name
        assert(temp_pdf.exists())
        target_pdf = self.pdf_name(fpath)
        temp_pdf.replace(target_pdf)

    def pdf_name(self, fpath):
        first_pass_pdf = self.dirs.build / ("1st_pass_" + fpath.with_suffix(".pdf").name)
        return first_pass_pdf

class LatexSecondPass(globber.FileGlobberMulti):
    """
    Second pass of latex compiling,
    post-bibliography resolution
    """

    def __init__(self, dirs:DootDirs, roots:list[pl.Path]):
        super().__init__("_tex::pass:two", dirs, roots, exts=[".tex"], rec=True)

    def subtask_detail(self, fpath, task):
        no_suffix = fpath.with_suffix("")
        task.update({"task_dep" : [f"_tex::pass:bibtex:{task['name']}"],
                     "file_dep" : [ self.dirs.temp / fpath.with_suffix(".aux").name,
                                    self.dirs.temp / fpath.with_suffix(".bbl").name,
                                   ],
                     "targets"  : [ self.dirs.build / fpath.with_suffix(".pdf").name],
                     "clean"    : True,
                     "params" : [
                         { "name"   : "interaction",
                           "short"  : "i",
                           "type"    : str,
                           "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
                           "default" : "nonstopmode",
                          },
                     ],
                     })
        return task

    def subtask_actions(self, fpath):
        build_cmd = partial(self.tex_cmd, fpath)
        return [CmdAction(build_cmd, shell=False),
	            CmdAction(build_cmd, shell=False),
                partial(self.move_pdf, fpath),
                ]

    def tex_cmd(self, fpath, interaction, task):
        no_suffix = fpath.with_suffix("")
        return ["pdflatex", f"-interaction={interaction}", f"-output-directory={self.dirs.temp}", no_suffix]

    def move_pdf(self, fpath, targets):
        temp_pdf   = self.dirs.temp  / fpath.with_suffix(".pdf").name
        assert(temp_pdf.exists())
        target_pdf = pl.Path(targets[0])
        temp_pdf.replace(target_pdf)

    

class LatexCheck(globber.FileGlobberMulti):
    """
    Run a latex pass, but don't produce anything,
    just check the syntax
    """

    def __init__(self, dirs:DootDirs, roots:list[pl.Path]):
        super().__init__("tex::check", dirs, roots, exts=['.tex'], rec=True)

    def subtask_detail(self, fpath, task):
        task.update({"file_dep" : [ fpath ],
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
        return ["pdflatex", "-draftmode", f"-interaction={interaction}", f"-output-directory={self.dirs.temp}", no_suffix]

class BibtexCheck(globber.FileGlobberMulti):
    """
    TODO
    """

    def __init__(self, dirs):
        super().__init__("bibtex::check", dirs, exts=['.bib'], rec=True)

    def subtask_detail(self, fpath, task):
        task.update({})
        return task

class BibtexBuildTask(globber.FileGlobberMulti):
    """
    Bibliography resolution pass
    """

    def __init__(self, dirs:DootDirs, roots):
        super().__init__("_tex::pass:bibtex", dirs, roots, exts=[".tex"], rec=True)

    def subtask_detail(self, fpath, task):
        aux_file = self.dirs.temp / fpath.with_suffix(".aux").name
        bbl_file = self.dirs.temp / fpath.with_suffix(".bbl").name

        task.update({"task_dep" : [f"tex::pass:one:{task['name']}"],
                     "file_dep" : [ self.dirs.temp / "combined.bib",
                                    aux_file ],
                     "targets"  : [ bbl_file ],
                     "clean"    : True,
                     })
        return task

    def subtask_actions(self, fpath):
        aux_file = self.dirs.temp  / fpath.with_suffix(".aux").name
        return [ partial(self.retarget_paths, aux_file),
                 CmdAction(self.maybe_run, shell=False),
                ]

    def retarget_paths(self, aux):
        """ Check if the aux file has bibdata, if it does mod it to use the concatenated bib data """
        reg     = re.compile(r"\\bibdata{(.+?)}")
        bib_loc =  str(self.dirs.temp / "combined.bib")
        has_bib = False
        print("Retargeting: ", aux)
        for line in fileinput.input(files=[aux], inplace=True):
            line_match = reg.match(line)
            if line_match is None:
                print(line.strip())
            else:
                has_bib = True
                print(r"\bibdata{" + bib_loc + "}")

        return { "has_bib" : has_bib }

    def maybe_run(self, task, dependencies, targets):
        """
        If bibdata has been found, run bibtex, otherwise do nothing
        """
        deps = { pl.Path(x).suffix : x for x in dependencies }

        if not bool(task.values['has_bib']):
            return ["touch", *targets]

        return ["bibtex",  deps['.aux']]


class BibtexConcatenateTask(DootTasker):
    """
    concatenate all found bibtex files
    to produce a master file for latex's use
    """
    def __init__(self, dirs:DootDirs):
        super().__init__("_tex::bib", dirs)

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.glob_bibs, self.concat_bibs ],
            "targets"  : [ self.dirs.temp / "combined.bib" ],
            "clean"    : True,
        })
        return task

    def glob_bibs(self, task):
        all_bibs : set[pl.Path] = set()
        for root in [self.dirs.data, self.dirs.src, self.dirs.docs]:
            all_bibs.update(list(root.rglob("**/*.bib")))

        return {
            "bibs" : list(str(x) for x in all_bibs),
        }

    def concat_bibs(self, targets, task):
        src_bibs : set[pl.Path] = task.values['bibs']

        with open(targets[0], 'w') as f:
            for bib in src_bibs:
                assert(pl.Path(bib).exists())
                f.write(pl.Path(bib).read_text() + "\n")

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
        "clean" : True
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


