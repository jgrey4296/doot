##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from functools import partial
from typing import Final

import doot
from doot import globber
from doot.tasker import DootTasker

##-- end imports


##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin

lint_config     : Final = doot.config.on_fail("pylint.toml", str).python.lint.config()
lint_exec       : Final = doot.config.on_fail("pylint", str).python.lint.exec()
lint_fmt        : Final = doot.config.on_fail("text", str).python.lint.output_format()
lint_out        : Final = doot.config.on_fail(f"report.lint", str).python.lint.output_name()
lint_grouped    : Final = doot.config.on_fail(True, bool).python.lint.grouped()
lint_error      : Final = doot.config.on_fail(False, bool).python.lint.error()

py_test_dir_fmt : Final = doot.config.on_fail("__test", str).python.test.dir_fmt()
py_test_args    : Final = doot.config.on_fail([], list).python.test.args()
py_test_out     : Final = pl.Path(doot.config.on_fail("result.test", str).python.test())

class InitPyGlobber(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin):
    """ ([src] -> src) add missing __init__.py's """

    def __init__(self, name=f"py::initpy", locs:DootLocData=None, roots=None, rec=False):
        super().__init__(name, locs, roots or [locs.src], rec=rec)
        self.ignores = ["__pycache__", ".git", "__mypy_cache__"]

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and bool(list(fpath.glob("*.py"))) and not (fpath / "__init__.py").exists():
            return self.control.keep
        return self.control.reject

    def subtask_detail(self, task, fpath=None):
        task['actions'] += [ self.cmd("touch", fpath / "__init__.py") ]
        return task

class PyLintTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """ ([root]) lint the package """

    def __init__(self, name=f"py::lint", locs:DootLocData=None, rec=None, exts=None):
        super().__init__(name, locs, [locs.root], rec=rec or not lint_grouped, exts=exts or [".py"])
        self.output = self.locs.on_fail(self.locs.build).lint_out()

    def set_params(self):
        return [
            {"name": "grouped", "type": bool, "default": lint_grouped, "short": "g"},
        ] + self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and bool(list(fpath.glob("*.py"))):
            return self.globc.accept
        return self.globc.discard


    def setup_detail(self, task):
        task.update({
            "verbosity" : 0,
            "targets"   : [ "pylint.toml" ],
            "uptodate"  : [ lambda task: pl.Path("pylint.toml").exists() ],
            'actions'   : [
                (self.log, ["Generating Pylint Config Toml", logmod.INFO]),
                self.cmd([lint_exec, "--generate-toml-config"], save="config"),
                (self.write_to, [pl.Path("pylint.toml"), "config"]),
            ]
        })
        return task

    def subtask_detail(self, task, fpath=None):
        if not self.args['grouped']:
            target = (self.output / task['name']).with_suffix(".lint")
        else:
            target = self.output / lint_out

        task.update({
            "actions"   : [
                (self.log, [f"Checking: {fpath}", logmod.INFO]),
                self.cmd(self.run_lint, fpath, save="lint"),
                (self.write_lint_report, [target]),
            ],
            "targets"   : [ target ],
            "clean"     : True,
        })
        return task

    def run_lint(self, fpath):
        args = [lint_exec, "--rcfile", lint_config, "--output-format", lint_fmt,
                "-E" if lint_error else None, "--exit-zero",
                ]
        lint_targets = self.glob_files(fpath, rec=lint_grouped)
        args += lint_targets
        return [x for x in args if x is not None]

    def write_lint_report(self, fpath, task):
        if lint_grouped:
            with open(fpath, 'a') as f:
                f.write("\n" + task.values['lint'])

        else:
            fpath.write_text(task.values['lint'])

class PyUnitTestGlob(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([root]) Run all project unit tests
    """

    def __init__(self, name=f"py::test", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.root], exts=[".py"], rec=rec)
        self.locs.ensure("build", task=name)
        self.output = self.locs.build

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and py_test_dir_fmt in fpath.name:
            return self.control.keep
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        target = self.output / py_test_out.with_stem(task['name'])
        task.update({
            "targets" : [ target ],
            "actions" : [ self.cmd(self.run_tests, fpath, save="results"),
                          (self.write_to, [target, "results"])
                         ]
        })
        return task

    def run_tests(self, fpath):
        args = ["python", "-X", "dev", "-m", "unittest", "discover", "-t", pl.Path()]
        args += py_test_args
        args.append(fpath)
        return args

class TODOPyParseRailroad(DootTasker):
    """
    python "$(PY_TOP)/util/build_railroad.py" --parser instal.parser.v1 --out "$(DOCBUILDDIR)"
    """

    pass
