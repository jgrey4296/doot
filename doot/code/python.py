##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd, src_dir

##-- end imports

def task_initpy() -> dict:
    """:: touch all __init__.py files """
	# TODO find ${PY_TOP} -type d -print0 | xargs -0 -I {} touch "{}/__init__.py"

    cmd  = ""
    args = []
    return {
        ## Required (callable | tuple(callable, *args, **kwargs))
        "actions"     : [ build_cmd(cmd, args) ],
    }

def task_lint() -> dict:
    """:: lint the package """
    # TODO add ignore / ignore-patterns / --ignore-paths

    data = datatoml['tool']['doit']['commands']['lint']
    cmd  = data['executable']
    args = [
        "--output-format", data['outfmt'],
        "--output", data['outfile'],
        "-E" if data['errors'] else "",
        datatoml['project']['name']
    ]


    return {
        "actions"   : [ build_cmd(cmd, args) ],
        "verbosity" : 2,
        "targets"   : [ "package.lint" ],
        "clean"     : True,
    }


## TODO run in -X dev mode, add warnings
def task_test() -> dict:
    """:: Task definition """
    data = datatoml['tool']['doit']['commands']['test']
    cmd  = "python"
    args = ["-m", "unittest", "discover",
            datatoml['project']['name'],
            "-p", datatoml['tool']['doit']['commands']['test']['pattern'],
            "-t", datatoml['project']['name'],
            "-s", "{start}"
            ]

    if data['verbose']:
        args.append("-v")

    if data['failfast']:
        args.append('-f')

    return {
        ## Required (callable | tuple(callable, *args, **kwargs))
        "actions"     : [ build_cmd(cmd, args) ],
        "params"      : [ {"name"    : "start",
                           "start"   : "-s",
                           "default" : datatoml['project']['name']
                           },
                          ]
    }


