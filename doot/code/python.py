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

    def get_actions(self, fpath):
        return [ self.touch_initpys ]

    def task_details(self, fpath, task):
        task.update({
            "meta" : { "focus" : fpath }
        })
        return task


def task_lint() -> dict:
    """:: lint the package """
    # TODO add ignore / ignore-patterns / --ignore-paths
    proj_name = data_toml['project']['name']
    def run_lint(fmt, executable, error):
        args = ["--output-format", fmt,
                "--output", "package.lint"
                ]
        if error:
            args.append("-E")

        args.append(proj_name)

        return f"{executable} " + " ".join(args)


    return {
        "actions"   : [ CmdAction(run_lint) ],
        "verbosity" : 2,
        "targets"   : [ "package.lint" ],
        "clean"     : True,
        "params"    : [
            { "name" : "fmt",
              "short" : "f",
              "type" : str,
              "default" : "",
             },
            { "name"    : "executable",
              "short"   : "e",
              "type"    : str,
              "default" : "pylint",
             },
            { "name"    : "error",
              "short"   : "x",
              "type"    : bool,
              "default" : False,
             },


            ],
    }


## TODO run in -X dev mode, add warnings
def task_test() -> dict:
    """
    Run all project unit tests
    """
    proj_name = data_toml['project']['name'],

    def run_tests(verbose, start, failfast, pattern, start):
        args = ["-m", "unittest", "discover",
                proj_name,
                "-p", pattern,
                "-t", proj_name,
                "-s", start,
                ]

        if verbose:
            args.append("-v")

        if failfast:
            args.append('-f')

        return f"python " + " ".join(args)

    return {
        "basename"    : "python::test",
        "actions"     : [ CmdAction(run_tests) ],
        "params"      : [
            {"name"    : "start",
             "short"   : "s",
             "type"    : str,
             "default" : data_toml['project']['name']
             },
            { "name"    : "verbose",
              "short"   : "v",
              "type"    : bool,
              "default" : False,
             },
            { "name"    : "pattern",
              "short"   : "p",
              "type"    : str,
              "default" : "*_tests.py"
              }
        ]
    }


