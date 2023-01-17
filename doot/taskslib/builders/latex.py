##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
import re
import fileinput

import doot
from doot import globber
from doot import tasker

##-- end imports

interaction_mode = doot.config.or_get("nonstopmode").tool.doot.tex.interaction()


class LatexMultiPass(globber.EagerFileGlobber):
    """
    ([src] -> build) Trigger both latex passes and the bibtex pass
    """

    def __init__(self, name="tex::build", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=['.tex'], rec=rec)


    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ self.dirs.build / fpath.with_suffix(".pdf").name ],
        })
        return task

class LatexFirstPass(globber.EagerFileGlobber, DootActions):
    """
    ([src] -> [temp, build]) First pass of running latex,
    pre-bibliography resolution
    """

    def __init__(self, name="text::pass:one", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True, interaction=interaction_mode):
        super().__init__(name, dirs, roots or [dirs.src], exts=[".tex"], rec=rec)
        self.interaction = interaction

    def set_params(self):
        return [
            { "name"   : "interaction",
              "short"  : "i",
              "type"    : str,
              "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
              "default" : self.interaction,
             },
        ]

    def subtask_detail(self, task, fpath=None):
        first_pass_pdf = self.pdf_path(fpath)
        temp_pdf = self.dirs.temp / fpath.with_suffix(".pdf").name
        task.update({
            "file_dep" : [ fpath ],
            "actions"  : [ self.cmd(self.compile_tex),
                           (self.move_to, [first_pass,pdf, temp_pdf])
                          ],
            "targets"  : [ self.dirs.temp / fpath.with_suffix(".aux").name,
                           first_pass_pdf,
                          ],
            "clean"    : True,
        })

        return task

    def compile_tex(self, dependencies):
        target = pl.Path(dependencies[0]).with_suffix("")
        return ["pdflatex",
                f"-interaction={self.args['interaction']}",
                f"-output-directory={self.dirs.temp}",
                target]

    def pdf_path(self, fpath):
        first_pass_pdf = self.dirs.build / ("1st_pass_" + fpath.with_suffix(".pdf").name)
        return first_pass_pdf

class LatexSecondPass(globber.EagerFileGlobber, DootActions):
    """
    ([src, temp] -> build) Second pass of latex compiling,
    post-bibliography resolution
    """

    def __init__(self, name="_tex::pass:two", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[".tex"], rec=rec)

    def set_params(self):
        return [
            { "name"   : "interaction",
              "short"  : "i",
              "type"    : str,
              "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
              "default" : "nonstopmode",
             },
        ]

    def subtask_detail(self, task, fpath=None):
        temp_pdf   = self.dirs.temp  / fpath.with_suffix(".pdf").name
        target_pdf = self.dirs.build / temp_pdf.name
        task.update({"file_dep" : [ self.dirs.temp / fpath.with_suffix(".aux").name,
                                    self.dirs.temp / fpath.with_suffix(".bbl").name,
                                   ],
                     "targets"  : [ target_pdf ],
                     "clean"    : True,
                     "actions" : [ self.cmd(self.tex_cmd, fpath),
	                               self.cmd(self.tex_cmd, fpath),
                                  (self.move_to, [fpath]),
                                  ]
                     })
        return task

    def tex_cmd(self, fpath):
        return ["pdflatex",
                f"-interaction={self.args['interaction']}",
                f"-output-directory={self.dirs.temp}",
                fpath.with_suffix("")]

    
class BibtexBuildPass(globber.EagerFileGlobber, DootActions):
    """
    ([src] -> temp) Bibliography resolution pass
    """

    def __init__(self, name="_tex::pass:bibtex", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[".tex"], rec=rec)

    def subtask_detail(self, task, fpath=None):
        aux_file = self.dirs.temp / fpath.with_suffix(".aux").name
        bbl_file = self.dirs.temp / fpath.with_suffix(".bbl").name

        task.update({"file_dep" : [ self.dirs.temp / "combined.bib",
                                    aux_file ],
                     "targets"  : [ bbl_file ],
                     "clean"    : True,
                     "actions" : [ (self.retarget_paths, [aux_file]),
                                   self.cmd(self.maybe_run),
                                  ]
                     })
        return task

    def retarget_paths(self, aux):
        """ Check if the aux file has bibdata, if it does mod it to use the concatenated bib data """
        reg     = re.compile(r"\\bibdata{(.+?)}")
        bib_loc =  str(self.dirs.temp / "combined.bib")
        has_bib = False
        print("Retargeting: ", aux)
        for line in fileinput.input(files=[aux], inplace=True, backup=".backup"):
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


class BibtexConcatenateSweep(globber.LazyFileGlobber):
    """
    ([src, data, docs] -> temp) concatenate all found bibtex files
    to produce a master file for latex's use
    """
    def __init__(self, name="_tex::bib", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src, dirs.data, dirs.docs], exts=[".bib"], rec=rec)
        self.target = dirs.temp / "combined.bib"

    def task_detail(self, task):
        task.update({
            "targets"  : [ self.target ],
            "clean"    : True,
        })
        return task

    def subtask_detail(self, task, fpath=None):
        task.update({
            "actions" : [(self.glob_and_add, [fpath])]
        })
        return task

    def glob_and_add(self, fpath, task):
        with open(self.target, 'w') as mainBib:
            for line in fileinput.input(files=self.glob_target(fpath)):
                print(line.strip(), file=mainBib)

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



def task_latex_rebuild():
    """ rebuild tex formats and metafonts, for handling outdated l3 layer errors """
    package_re = re.compile("^i (.+?):.+?$")

    def build_install_cmd(task):
        packages = [package_re.match(x)[1] for x in task.values['installed'].split("\n") if package_re.match(x)]
        return ["tlmgr", "install", "--reinstall", *packages]
    
    return {
        "basename" : "tex::rebuild",
        "actions" : [ DootActions.cmd(None, ["fmtutil",  "--all"]),
                      DootActions.cmd(None, ["tlmgr",  "list", "--only-installed"], save="installed"),
                      DootActions.cmd(None, build_install_cmd)
        ],
    }


