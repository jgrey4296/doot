##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

# TODO target into build_dir
def task_plantuml_json():
    """
    Generate uml diagrams from json
    """
    cmd1 = "cat ?"
    cmd2 = "awk 'BEGIN {print \"@startjson\"} END {print \"@endjson\"} {print $0}'"
    cmd3 = "plantuml -p"
    output =

    full = f"{cmd1} | {cmd2} | {cmd3} > {output}"
    return {
        "actions"  : [full],
        "targets"  : ["json_vis.png"],
        "file_dep" : ["something.json"],
    }

def task_plantuml():
    """
    run plantuml on a specification
    """
    cmd = "plantuml"
    args = ["-filename", "{targets}", "{file_dep}"]
    return {
        "actions"  : [build_cmd(cmd, args)],
        "targets"  : ["schema_uml.png"],
        "file_dep" : ["schema.pu"],
    }

def task_plantuml_text():
    """
    run plantuml on a spec for text output
    """
    cmd = "plantuml"
    args = ["-ttxt", "-filename", "{targets}", "{file_dep}"],
    return {
        "actions"  : [build_cmd(cmd, args)],
        "targets"  : ["schema_uml.txt"],
        "file_dep" : ["schema.pu"],
    }
