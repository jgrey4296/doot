##-- imports
from __future__ import annotations

import pathlib as pl
from functools import partial
from doit.action import CmdAction

import doot
from doot.utils import globber
from doot.utils.locdata import DootLocData
from doot.utils.tasker import DootTasker
##-- end imports

prefix = doot.config.or_get("python").tool.doot.python.prefix()

lint_exec       = doot.config.or_get("pylint").tool.doot.python.lint.exec()
lint_fmt        = doot.config.or_get("text").tool.doot.python.lint.output_format()
lint_out        = pl.Path(doot.config.or_get(f"report.lint").tool.doot.python.lint.output_name())
lint_grouped    = doot.config.or_get(True).tool.doot.python.lint.grouped()
lint_error      = doot.config.or_get(False).tool.doot.python.lint.error()

py_test_dir_fmt = doot.config.or_get("__test").tool.doot.python.test.dir_fmt()
py_test_args    = doot.config.or_get([]).tool.doot.python.test.args()
py_test_out     = pl.Path(doot.config.or_get("result.test").tool.doot.python.test())

def task_buildvenv():
    return {
        "basename" : f"{prefix}::venv",
        "actions" : [],
        }

class InitPyGlobber(globber.DirGlobber):

    def __init__(self, dirs:DootLocData, rec=False):
        super().__init__(f"{prefix}::initpy", dirs, [dirs.src], rec=rec)
        self.ignores = ["__pycache__", ".git", "__mypy_cache__"]

    def subtask_detail(self, fpath, task):
        task['meta'].update({"focus" : fpath})
        return task

    def subtask_actions(self, fpath):
        return [ self.touch_initpys ]

    def touch_initpys(self, task):
        queue = [ task.meta['focus'] ]
        while bool(queue):
            current = queue.pop()
            if current.is_file():
                continue
            if current.name in self.ignores:
                continue

            queue += list(current.iterdir())

            inpy = current / "__init__.py"
            inpy.touch()


class PyLintTask(globber.DirGlobber):
    """ lint the package """

    def __init__(self, dirs:DootLocData):
        super().__init__(f"{prefix}::lint", dirs, [dirs.root], rec=not lint_grouped)

    def filter(self, fpath):
        return (fpath / "__init__.py").exists()

    def setup_detail(self, task):
        task.update({ "verbosity" : 0,
                      "targets"   : [ "pylint.toml" ],
                      "uptodate"  : [False],
                     })

        if not pl.Path("pylint.toml").exists():
            task['actions'] += [ CmdAction([lint_exec, "--generate-toml-config"], shell=False, save_out="config"),
                                 lambda task: pl.Path("pylint.toml").write_text(task.values['config']) ]

        return task

    def subtask_detail(self, fpath, task):
        target = lint_out if lint_grouped else lint_out.with_stem(task['name'])
        task.update({
            "targets" : [ self.dirs.build / target ],
            "clean"   : True,
        })
        task['meta'].update({
            "format" : lint_fmt,
            "exec"   : lint_exec,
            "error"  : lint_error,
        })
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(self.run_lint, shell=False) ]

    def run_lint(self, task, targets):
        args = [task.meta['exec'],
                "--rcfile", "pylint.toml",
                "--output-format", task.meta['format'],
                "--output", targets[0],
                "-E" if task.meta['error'] else None,
                "--exit-zero",
                "-v",
                self.dirs.src
                ]

        return [x for x in args if x is not None]


    def gen_toml(self):
        return "\n".join([
            "[tool.doot.python.lint]",
            "exec = \"pylint\"",
            "output-format = \"text\"",
            "output-name = \"lint.results\"",
            "error = false",
            "grouped = false",
            ])


class PyUnitTestGlob(globber.DirGlobber):
    """
    Run all project unit tests
    """

    def __init__(self, dirs:DootLocData):
        super().__init__(f"{prefix}::test", dirs, [dirs.root], exts=[".py"], rec=True)

    def filter(self, fpath):
        return py_test_dir_fmt in fpath.name

    def subtask_detail(self, fpath, task):
        target = py_test_out if lint_grouped else py_test_out.with_stem(task['name'])
        task.update({"targets" : [ self.dirs.build / target ],
                     })
        task['meta'].update({"dir" : fpath})
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(self.run_tests, shell=False, save_out="results"),
                 self.write_results,
                ]

    def write_results(self, task, targets):
        pl.Path(targets[0]).write_text(task.values['results'])

    def run_tests(self, task):
        args = ["python", "-X", "dev", "-m", "unittest", "discover", "-t", pl.Path()]
        args += py_test_args
        args.append(task.meta['dir'])
        return args

    def gen_toml(self):
        return "\n".join([
            "[tool.doot.python.test]",
            "dir-fmt = \"__test\"",
            "args    = []",
            ])


class PyTestGlob(globber.DirGlobber):
    """
    Run all project unit tests
    """

    def __init__(self, dirs:DootLocData):
        super().__init__(f"{prefix}::test", dirs, [dirs.src], exts=[".py"], rec=True)

    def filter(self, fpath):
        return py_test_dir_fmt in fpath.name

    def subtask_detail(self, fpath, task):
        target = py_test_out if lint_grouped else py_test_out.with_stem(task['name'])
        task.update({"targets" : [ target ],
                     })
        task['meta'].update({"dir" : fpath})
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(self.run_tests) ]

    def run_tests(self, task):
        args = ["pytest", "-X", "dev"]
        args += py_test_args
        args.append(task.meta['dir'])
        return args

    def gen_toml(self):
        return "\n".join([
            "[tool.doot.python.test]",
            "dir-fmt = \"__test\"",
            "args    = []",
            ])


class PyParseRailroad(DootTasker):
    """
    python "$(PY_TOP)/util/build_railroad.py" --parser instal.parser.v1 --out "$(DOCBUILDDIR)"
    """
    pass
