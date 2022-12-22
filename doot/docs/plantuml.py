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

##-- dir check
plant_check = CheckDir(paths=[plant_dir], name="plantuml", task_dep=["_checkdir::build"])

##-- end dir check

def task_plantuml():
    """
    run plantuml on a specification, generating target.'ext's
    """
    for path in build_dir.glob("**/*.plantuml"):
        cmd        = "plantuml"
        args       = ["-tpng",
                      "-output", plant_dir.resolve(),
                      "-filename", "{targets}",
                      "{dependencies}"
                      ]
        targ_fname = path.with_suffix(".png")
        yield {
            "basename" : "plantuml::png",
            "name"     : targ_fname.stem,
            "actions"  : [ build_cmd(cmd, args)],
            "targets"  : [ plant_dir / targ_fname.name],
            "file_dep" : [ path ],
            "task_dep" : [ f"plantuml::check:{targ_fname.stem}" ],
            "params"   : [ { "name"    : "ext",
                             "short"   : "e",
                             "type"    : str,
                             "default" : "png" },
                          ],
            "clean"     : True,
        }

def task_plantuml_text():
    """
    run plantuml on a spec for text output
    """
    for path in build_dir.glob("**/*.plantuml"):
        cmd  = "plantuml"
        args = ["-ttxt",
                "-output", plant_dir.resolve(),
                "-filename", "{targets}",
                "{dependencies}"
                ]
        targ_fname = path.with_suffix(".atxt")
        yield {
            "basename" : "plantuml::txt",
            "name"     : targ_fname.stem,
            "actions"  : [ build_cmd(cmd, args)],
            "targets"  : [ plant_dir / targ_fname.name],
            "file_dep" : [ path ],
            "task_dep" : [ f"plantuml::check:{targ_fname.stem}" ],
            "clean"    : True,
        }

def task_plantuml_check():
    """
    check syntax of plantuml files
    """
    for path in build_dir.glob("**/*.plantuml"):
        cmd        = "plantuml"
        args       = [ "-checkonly", "{dependencies}"]
        yield {
            "basename" : "plantuml::check",
            "name"     : path.stem,
            "actions"  : [ build_cmd(cmd, args)],
            "file_dep" : [ path ],
            "uptodate" : [False],
        }

