##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

plant_dir = build_dir / "plantuml"

def task_plantuml_json():
    """
    Generate uml diagrams from json
    """
    cmd1 = "cat {file_dep}"
    cmd2 = "awk 'BEGIN {print \"@startjson\"} END {print \"@endjson\"} {print $0}'"
    cmd3 = "plantuml -p"

    full_cmd = f"{cmd1} | {cmd2} | {cmd3} > {targets}"
    return {
        "actions"  : [full_cmd],
        "targets"  : [plant_dir / "json_vis.png"],
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
        "targets"  : [plant_dir / "schema_uml.png"],
        "file_dep" : [plant_dir / "schema.pu"],
    }

def task_plantuml_text():
    """
    run plantuml on a spec for text output
    """
    cmd = "plantuml"
    args = ["-ttxt", "-filename", "{targets}", "{file_dep}"],
    return {
        "actions"  : [build_cmd(cmd, args)],
        "targets"  : [plant_dir / "schema_uml.txt"],
        "file_dep" : [plant_dir / "schema.pu"],
    }
