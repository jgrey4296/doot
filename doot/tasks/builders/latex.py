##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
import re
import fileinput
from typing import Final

import logging as logmod
import doot
from doot import globber, tasker
from doot.mixins.delayed import DelayedMixin

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.calc_deps import CalcDepsMixin

interaction_mode  : Final = doot.config.on_fail("nonstopmode", str).tex.interaction()
tex_dep           : Final = doot.config.on_fail("tex.dependencies", str).text.dep_file()

def task_latex_install():
    """
    install dependencies for the latex document
    """
    if not pl.Path(tex_dep).exists():
        return None

    return {
        "basename" : "tex::install",
        "actions"  : [
            # TODO log message
            lambda: { "tex_deps" : list({x for x in pl.Path(tex_dep).read_text().split("\n") if bool(x)}) },
            CommanderMixin.cmd(None, lambda task: ["tlmgr", "--usermode",  "install", *task.values['tex_deps']]),
            ],
        "file_dep" : [ tex_dep ],
    }

def task_latex_requirements():
    """
    create a requirements file of latex packages
    """
    return {
        "basename" : "tex::requirements",
        "actions" : [
            # TODO log msg
            CommanderMixin.cmd(None, ["tlmgr", "--usermode", "list", "--only-installed", "--data", "name"], save="reqs"),
            (CommanderMixin.write_to, [None, tex_dep, "reqs"])
        ],
        "targets" : [ tex_dep ],
        "clean" : True
    }

def task_latex_rebuild():
    """ rebuild tex formats and metafonts, for handling outdated l3 layer errors """
    package_re = re.compile("^i (.+?):.+?$")

    return {
        "basename" : "tex::rebuild",
        "actions" : [
            # TODO log msg
            CommanderMixin.cmd(None, ["fmtutil",  "--all"]),
            CommanderMixin.cmd(None, ["tlmgr",  "list", "--only-installed"], save="installed"),
            lambda task: { "packages" : [package_re.match(x)[1] for x in task.values['installed'].split("\n") if package_re.match(x)] },
            CommanderMixin.cmd(None, lambda task: ["tlmgr", "install", "--reinstall", *task.values['packages']]),
        ],
    }

class LatexMultiPass(globber.DootEagerGlobber):
    """
    ([src] -> build) Trigger both latex passes and the bibtex pass
    """

    def __init__(self, name="tex::build", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=['.tex'], rec=rec)
        self.locs.ensure("build", task=name)

    def filter(self, fpath):
        return fpath.is_file()

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ self.locs.build / fpath.with_suffix(".pdf").name ],
            "private"  : False,
        })
        return task

class LatexFirstPass(globber.DootEagerGlobber, FilerMixin, CommanderMixin):
    """
    ([src] -> [temp, build]) First pass of running latex,
    pre-bibliography resolution
    """

    def __init__(self, name="tex::pass:one", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True, interaction=interaction_mode):
        super().__init__(name, locs, roots or [locs.src], exts=[".tex"], rec=rec)
        self.interaction = interaction
        self.locs.ensure("temp", "build", task=name)

    def filter(self, fpath):
        return fpath.is_file()

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
        temp_pdf       = self.locs.temp / fpath.with_suffix(".pdf").name
        task.update({
            "file_dep" : [ fpath ],
            "actions"  : [
                (self.log, ["Running Pass 1", logmod.INFO]),
                self.make_cmd(self.compile_tex),
                (self.move_to, [first_pass_pdf, temp_pdf])
            ],
            "targets"  : [ self.locs.temp / fpath.with_suffix(".aux").name,
                           first_pass_pdf,
                          ],
            "clean"    : True,
        })

        return task

    def compile_tex(self, dependencies):
        target = pl.Path(dependencies[0]).with_suffix("")
        return ["pdflatex",
                f"-interaction={self.args['interaction']}",
                f"-output-directory={self.locs.temp}",
                target]

    def pdf_path(self, fpath):
        first_pass_pdf = self.locs.build / ("1st_pass_" + fpath.with_suffix(".pdf").name)
        return first_pass_pdf

class LatexSecondPass(globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([src, temp] -> build) Second pass of latex compiling,
    post-bibliography resolution
    """

    def __init__(self, name="_tex::pass:two", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=[".tex"], rec=rec)
        self.locs.ensure("temp", "build", task=name)

    def set_params(self):
        return [
            { "name"   : "interaction", "short"  : "i", "type"    : str,
              "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
              "default" : "nonstopmode",
             },
        ]

    def filter(self, fpath):
        return fpath.is_file()

    def subtask_detail(self, task, fpath):
        temp_pdf   = self.locs.temp  / fpath.with_suffix(".pdf").name
        target_pdf = self.locs.build / temp_pdf.name
        task.update({
            "file_dep" : [ self.locs.temp / fpath.with_suffix(".aux").name,
                           self.locs.temp / fpath.with_suffix(".bbl").name,
                          ],
            "targets"  : [ target_pdf ],
            "clean"    : True,
            "actions" : [
                (self.log, ["Running Pass 2", logmod.INFO]),
                self.make_cmd(self.tex_cmd, fpath),
	            self.make_cmd(self.tex_cmd, fpath),
                (self.move_to, [target_pdf, temp_pdf]),
            ]
        })
        return task

    def tex_cmd(self, fpath):
        return ["pdflatex",
                f"-interaction={self.args['interaction']}",
                f"-output-directory={self.locs.temp}",
                fpath.with_suffix("")]

class BibtexBuildPass(globber.DootEagerGlobber, CommanderMixin):
    """
    ([src] -> temp) Bibliography resolution pass
    """

    def __init__(self, name="_tex::pass:bibtex", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=[".tex"], rec=rec)
        self.locs.ensure("temp", task=name)

    def filter(self, fpath):
        return fpath.is_file()

    def subtask_detail(self, task, fpath=None):
        aux_file = self.locs.temp / fpath.with_suffix(".aux").name
        bbl_file = self.locs.temp / fpath.with_suffix(".bbl").name

        task.update({
            "file_dep" : [ self.locs.temp / "combined.bib",
                           aux_file ],
            "targets"  : [ bbl_file ],
            "clean"    : True,
            "actions" : [
                (self.log, ["Running Bibtex Pass", logmod.INFO]),
                (self.retarget_paths, [aux_file]),
                self.make_cmd(self.maybe_run),
            ]
        })
        return task

    def retarget_paths(self, aux):
        """ Check if the aux file has bibdata, if it does mod it to use the concatenated bib data """
        reg     = re.compile(r"\\bibdata{(.+?)}")
        bib_loc =  str(self.locs.temp / "combined.bib")
        has_bib = False
        print("Retargeting: ", aux)
        for line in fileinput.input(files=[aux], inplace=True, backup=".backup"):
            line_match = reg.match(line)
            if line_match is None:
                print(line, end="")
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

class BibtexConcatenateSweep(CalcDepsMixin, tasker.DootTasker):
    """
    ([src, data, docs] -> temp) concatenate all found bibtex files
    to produce a master file for latex's use
    """

    def __init__(self, name="_tex::bib", locs:DootLocData=None):
        super().__init__(name, locs)
        self.output   = locs.temp / "combined.bib"
        self.all_bibs = set()
        self.locs.ensure("data", "docs", task=name)

    def setup_detail(self, task):
        task.update({
            "actions" :  [ self.glob_bibs ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                (self.log, ["Combining Bibtex", logmod.INFO]),
                self.concat_bibs,
            ],
            "targets"  : [ self.output],
            "clean"    : True,
        })
        return task

    def calc_action(self):
        return { "file_dep": list(self.all_bibs) }

    def glob_bibs(self):
        self.all_bibs.update(self.locs.src.rglob("*.bib"))
        self.all_bibs.update(self.locs.data.rglob("*.bib"))
        self.all_bibs.update(self.locs.docs.rglob("*.bib"))

    def concat_bibs(self):
        with open(self.output, "w") as catbib:
            for line in fileinput.input(files=self.all_bibs):
                print(line, end="", file=catbib)
