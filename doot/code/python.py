##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

from doot import build_dir, data_toml, src_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber

##-- end imports

lint_exec    = data_toml.or_get("pylint").tool.doot.python.lint.exec()
lint_fmt     = data_toml.or_get("text").tool.doot.python.lint.output_format()
lint_out     = data_toml.or_get("lint.result").tool.doot.python.lint.output_name()
lint_error   = data_toml.or_get(False).tool.doot.python.lint.error()
py_build_dir = build_dir / "python"

py_test_dir_fmt = data_toml.or_get("__test").tool.doot.python.test.dir_fmt()
py_test_args = data_toml.or_get([]).tool.doot.python.test.args()

class InitPyGlobber(globber.DirGlobber):

    def __init__(self, targets=data_dirs, rec=False):
        super().__init__("py::initpy", [], [src_dir], rec=rec)
        self.ignores = ["__pycache__", ".git", "__mypy_cache__"]

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

    def subtask_actions(self, fpath):
        return [ self.touch_initpys ]

    def subtask_detail(self, fpath, task):
        task['meta'].update({"focus" : fpath})
        return task


class PyLintTask(globber.DirGlobber):
    """:: lint the package """

    def __init__(self):
        super().__init__("python::lint", [], [src_dir], rec=False)

    def run_lint(self, task):
        args = ["--output-format", task.meta['format'],
                "--output", py_build_dir / task.meta["output"],
                ]
        if task.meta['error']:
            args.append("-E")

        args.append(proj_name)
        exec_cmd = task.meta['exec']
        cmd_args = " ".join(str(x) for x in args)
        return f"{exec_cmd} {cmd_args}"

    def subtask_actions(self, fpath):
        return [self.run_lint]

    def subtask_detail(self, fpath, task):
        task.update({})
        task['meta'].update({
            "format" : lint_fmt,
            "output" : lint_out,
            "exec"   : lint_exec,
            "error"  : lint_error,
            })
        return task

    def gen_toml(self):
        return "\n".join([
            "[tool.doot.python.lint]",
            "exec = \"pylint\"",
            "output-format = \"text\"",
            "output-name = \"lint.results\"",
            "error = false",
            ])

class PyTestGlob(globber.DirGlobber):
    """
    Run all project unit tests
    """

    def __init__(self):
        super().__init__("python::test", [".py"], [src_dir], rec=True, filter_fn=self.is_test_dir)

    def is_test_dir(self, fpath):
        return py_test_dir_fmt in fpath.name:

    def run_tests(self, task):
        args = ["-X", "dev", "-t", pl.Path()] + py_test_args
        arg_str = " ".join(args)
        return f"python -m unittest discover {arg_str} {task.meta['dir']}"

    def subtask_actions(self, fpath):
        return [self.run_tests]
    
    def subtask_detail(self, fpath, task):
        task.update({})
        task['meta'].update({"dir" : fpath})
        return task

    def gen_toml(self):
        return "\n".join([
            "[tool.doot.python.test]",
            "dir-fmt = \"__test\"",
            "args    = []",
            ])
