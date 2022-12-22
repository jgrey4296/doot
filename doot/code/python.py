##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd, src_dir

##-- end imports

def task_initpy() -> dict:
    """:: touch all __init__.py files """
    def touch_initpys():
        for path in src_dir.rglob("*"):
            if path.is_file():
                continue
            parts = path.parts
            if any(x in parts for x in ["__pycache__", ".git", "__mypy_cache__"]):
                continue

            inpy = path / "__init__.py"
            if not inpy.exists():
                inpy.touch()


    
    return {
        "basename"    : "python::initpys",
        "actions"     : [ touch_initpys ],
    }

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


