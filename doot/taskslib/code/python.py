##-- imports
from __future__ import annotations

import pathlib as pl
from functools import partial

import doot
from doot import globber
from doot.tasker import DootTasker, DootActions
##-- end imports

prefix = doot.config.or_get("py").tool.doot.python.prefix()

lint_exec       = doot.config.or_get("pylint").tool.doot.python.lint.exec()
lint_fmt        = doot.config.or_get("text").tool.doot.python.lint.output_format()
lint_out        = doot.config.or_get(f"report.lint").tool.doot.python.lint.output_name()
lint_grouped    = doot.config.or_get(True).tool.doot.python.lint.grouped()
lint_error      = doot.config.or_get(False).tool.doot.python.lint.error()

py_test_dir_fmt = doot.config.or_get("__test").tool.doot.python.test.dir_fmt()
py_test_args    = doot.config.or_get([]).tool.doot.python.test.args()
py_test_out     = pl.Path(doot.config.or_get("result.test").tool.doot.python.test())

def gen_toml(self):
    return "\n".join(["[tool.doot.python.lint]",
                      "exec = \"pylint\"",
                      "output-format = \"text\"",
                      "output-name = \"lint.results\"",
                      "error = false",
                      "grouped = false",
                      "[tool.doot.python.test]",
                      "dir-fmt = \"__test\"",
                      "args    = []",
                      ])


class InitPyGlobber(globber.DirGlobber, DootActions):
    """ ([src] -> src) add missing __init__.py's """
    gen_toml = gen_toml

    def __init__(self, name=f"{prefix}::initpy", dirs:DootLocData=None, roots=None, rec=False):
        super().__init__(name, dirs, roots or [dirs.src], rec=rec)
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


class PyLintTask(globber.DirGlobber, DootActions):
    """ ([root]) lint the package """

    gen_toml = gen_toml

    def __init__(self, name=f"{prefix}::lint", dirs:DootLocData=None, rec=None):
        super().__init__(name, dirs, [dirs.root], rec=rec or not lint_grouped)

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
            target = target.with_stem(task.name)
        else:
            target = self.dirs.build / lint_out

        task.update({
            "clean"   : True,
            "actions" : [ self.cmd(self.run_lint) ],
            "target"  : [ target ]
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
                self.dirs.src
                ]

        return [x for x in args if x is not None]




class PyUnitTestGlob(globber.DirGlobber, DootActions):
    """
    ([root]) Run all project unit tests
    """

    gen_toml = gen_toml

    def __init__(self, name=f"{prefix}::test", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.root], exts=[".py"], rec=rec)

    def filter(self, fpath):
        if py_test_dir_fmt in fpath.name:
            return self.control.keep

    def subtask_detail(self, task, fpath=None):
        target = py_test_out if lint_grouped else py_test_out.with_stem(task['name'])
        task.update({"targets" : [ self.dirs.build / target ],
                     "actions" : [ self.cmd(self.run_tests, fpath, save="results"),
                                   (self.write_to, [target, "results"])
                                  ]
                     })

    def run_tests(self, fpath, task):
        args = ["python", "-X", "dev", "-m", "unittest", "discover", "-t", pl.Path()]
        args += py_test_args
        args.append(fpath)
        return args



class PyTestGlob(globber.DirGlobber, DootActions):
    """
    ([src]) Run all project unit tests
    """

    gen_toml = gen_toml

    def __init__(self, name=f"{prefix}::test", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[".py"], rec=rec)

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

    gen_toml = gen_toml

    pass
