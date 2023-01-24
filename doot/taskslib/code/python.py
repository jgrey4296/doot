##-- imports
from __future__ import annotations

import pathlib as pl
from functools import partial
from typing import Final

import doot
from doot import globber
from doot.tasker import DootTasker, ActionsMixin
##-- end imports

prefix          : Final = doot.config.on_fail("py", str).tool.doot.python.prefix()

lint_exec       : Final = doot.config.on_fail("pylint", str).tool.doot.python.lint.exec()
lint_fmt        : Final = doot.config.on_fail("text", str).tool.doot.python.lint.output_format()
lint_out        : Final = doot.config.on_fail(f"report.lint", str).tool.doot.python.lint.output_name()
lint_grouped    : Final = doot.config.on_fail(True, bool).tool.doot.python.lint.grouped()
lint_error      : Final = doot.config.on_fail(False, bool).tool.doot.python.lint.error()

py_test_dir_fmt : Final = doot.config.on_fail("__test", str).tool.doot.python.test.dir_fmt()
py_test_args    : Final = doot.config.on_fail([], list).tool.doot.python.test.args()
py_test_out     : Final = pl.Path(doot.config.on_fail("result.test", str).tool.doot.python.test())


class InitPyGlobber(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """ ([src] -> src) add missing __init__.py's """

    def __init__(self, name=f"{prefix}::initpy", locs:DootLocData=None, roots=None, rec=False):
        super().__init__(name, locs, roots or [locs.src], rec=rec)
        self.ignores = ["__pycache__", ".git", "__mypy_cache__"]

    def filter(self, fpath):
        if fpath.name[0] in "_.":
            return self.control.reject
        return self.control.accept

    def subtask_detail(self, task, fpath=None):
        task['actions'] += [ (self.touch_initpys, [fpath]) ]
        return task

    def touch_initpys(self, fpath):
        queue = [ fpath ]
        while bool(queue):
            current = queue.pop()
            if current.is_file():
                continue
            if current.name in self.ignores:
                continue

            queue += list(current.iterdir())

            inpy = current / "__init__.py"
            inpy.touch()


class PyLintTask(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """ ([root]) lint the package """


    def __init__(self, name=f"{prefix}::lint", locs:DootLocData=None, rec=None):
        super().__init__(name, locs, [locs.root], rec=rec or not lint_grouped)

    def filter(self, fpath):
        return (fpath / "__init__.py").exists()

    def setup_detail(self, task):
        task.update({ "verbosity" : 0,
                      "targets"   : [ "pylint.toml" ],
                      'actions' : [ self.cmd([lint_exec, "--generate-toml-config"], save="config"),
                                    (self.write_to, [pl.Path("pylint.toml"), "config"]),
                                   ]
                      })
        return task

    def subtask_detail(self, task, fpath=None):
        if not lint_grouped:
            target = fpath.with_stem(task.name)
        else:
            target = self.locs.build / lint_out

        task.update({
            "clean"   : True,
            "actions" : [ self.cmd(self.run_lint) ],
            "targets" : [ target ]
        })
        return task


    def run_lint(self, targets, task):
        args = [lint_exec,
                "--rcfile", "pylint.toml",
                "--output-format", lint_format,
                "--output", targets,
                "-E" if lint_error else None,
                "--exit-zero",
                "-v",
                self.locs.src
                ]

        return [x for x in args if x is not None]




class PyUnitTestGlob(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    ([root]) Run all project unit tests
    """


    def __init__(self, name=f"{prefix}::test", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.root], exts=[".py"], rec=rec)

    def filter(self, fpath):
        if py_test_dir_fmt in fpath.name:
            return self.control.keep

    def subtask_detail(self, task, fpath=None):
        target = py_test_out if lint_grouped else py_test_out.with_stem(task['name'])
        task.update({"targets" : [ self.locs.build / target ],
                     "actions" : [ self.cmd(self.run_tests, fpath, save="results"),
                                   (self.write_to, [target, "results"])
                                  ]
                     })

    def run_tests(self, fpath, task):
        args = ["python", "-X", "dev", "-m", "unittest", "discover", "-t", pl.Path()]
        args += py_test_args
        args.append(fpath)
        return args



class PyTestGlob(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    ([src]) Run all project unit tests
    """


    def __init__(self, name=f"{prefix}::test", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=[".py"], rec=rec)

    def filter(self, fpath):
        if py_test_dir_fmt in fpath.name:
            return self.control.keep

    def subtask_detail(self, task, fpath=None):
        target = py_test_out if lint_grouped else py_test_out.with_stem(task['name'])
        task.update({"targets" : [ target ],
                     "actions" : [ self.cmd(self.run_tests, fpath) ]
                     })
        return task

    def run_tests(self, fpath, task):
        args = ["pytest", "-X", "dev"]
        args += py_test_args
        args.append(fpath)
        return args


class PyParseRailroad(DootTasker):
    """
    python "$(PY_TOP)/util/build_railroad.py" --parser instal.parser.v1 --out "$(DOCBUILDDIR)"
    """


    pass
