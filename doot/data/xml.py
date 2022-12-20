##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doit.action import CmdAction
from doot import build_dir, data_toml, src_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

# xmlschema, xsdata, xsdata-plantuml, generateDS
# http://www.davekuhlman.org/generateDS.html
# https://pyxb.sourceforge.net/
# https://xmlschema.readthedocs.io/en/latest/
# https://github.com/tefra/xsdata-plantuml
# https://python-jsonschema.readthedocs.io/en/stable/

data_dirs = [pl.Path(x) for x in data_toml.tool.doot.xml.data_dirs if pl.Path(x).exists()]
rec_dirs = [pl.Path(x) for x in data_toml.tool.doot.xml.recursive_dirs if pl.Path(x).exists()]

xml_gen_dir   = src_dir / "_generated"
xml_build_dir = build_dir / "xml"
schema_dir    = xml_build_dir   / "schema"
elements_dir  = xml_build_dir   / "elements"
visual_dir    = xml_build_dir   / "visual"

##-- dir checks
xml_dir_check = CheckDir(paths=[xml_build_dir,
                                schema_dir,
                                elements_dir,
                                visual_dir,
                                xml_gen_dir,
                                ], name="xml", task_dep=["_checkdir::build"])

##-- end dir checks


class XmlElementsTask:
    def __init__(self):
        self.create_doit_tasks = self.build

    def glob_target(self, targets, task):
        xmls = " ".join(f"'{x}'" for x in pl.Path(task.meta['focus']).glob("*.xml") if x.is_file())
        return f"xml el -u {xmls}" + " > {targets}"

    def glob_rec_target(self, targets, task):
        xmls = " ".join(f"'{x}'" for x in pl.Path(task.meta['focus']).rglob("*.xml") if x.is_file())
        return f"xml el -u {xmls}" + " > {targets}"

    def build(self):
        for targ in data_dirs:
            targ_fname = "_".join(targ.with_suffix(".elements").parts[-2:])
            yield {
                "basename" : "xml::elements",
                "name"     : targ.name,
                "actions"  : [ CmdAction(self.glob_target)],
                "targets"  : [ elements_dir / targ_fname ],
                "task_dep" : ["_checkdir::xml"],
                "meta"     : { "focus" : targ },
                "clean"    : True
            }

        for targ in rec_dirs:
            targ_fname = "_".join(targ.with_suffix(".rec_elements").parts[-2:])
            yield {
                "basename" : "xml::elements.rec",
                "name"     : targ.name,
                "actions"  : [ CmdAction(self.glob_rec_target)],
                "targets"  : [ elements_dir / targ_fname ],
                "task_dep" : ["_checkdir::xml"],
                "meta"     : { "focus" : targ },
                "clean"    : True
            }


class XmlSchemaTask:
    """
    Generate xml schema for directories of xml files
    """
    def __init__(self):
        self.create_doit_tasks = self.build
        self.cmd               = "trang"

    def glob_target(self, targets, task):
        xmls = " ".join(f"'{x}'" for x in pl.Path(task.meta['focus']).glob("*.xml") if x.is_file())
        return f"{self.cmd} {xmls}" + " {targets}"

    def glob_rec_target(self, targets, task):
        xmls = " ".join(f"'{x}'" for x in pl.Path(task.meta['focus']).rglob("*.xml") if x.is_file())
        return f"{self.cmd} {xmls}" + " {targets}"

    def build(self):
        for targ in data_dirs:
            targ_fname = "_".join((targ / "trang").with_suffix(".xsd").parts[-3:])
            yield {
                "basename" : "xml::schema",
                "name"     : targ.name,
                "actions"  : [ CmdAction(self.glob_target)],
                "targets"  : [ schema_dir / targ_fname ],
                "task_dep" : ["_checkdir::xml"],
                "meta"     : { "focus" : targ },
                "clean"    : True
            }

        for targ in rec_dirs:
            targ_fname = "_".join((targ / "trang_rec").with_suffix(".xsd").parts[-3:])
            yield {
                "basename" : "xml::schema.rec",
                "name"     : targ.name,
                "actions"  : [ CmdAction(self.glob_rec_target)],
                "targets"  : [ schema_dir / targ_fname ],
                "task_dep" : ["_checkdir::xml"],
                "meta"     : { "focus" : targ },
                "clean"    : True
            }



class XmlPythonSchemaRaw:
    def __init__(self):
        self.create_doit_tasks = self.build
        self.cmd = "xsdata"

    def glob_target(self, targets, task):
        args = ["generate",
                "-p", task.meta['package'], # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                str(task.meta['focus']) ]
        return f"{self.cmd} " + " ".join(args)

    def glob_rec_target(self, targets, task):
        args = ["generate",
                "-r", # recursive
                "-p", task.meta['package'], # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                str(task.meta['focus']) ]
        return f"{self.cmd} " + " ".join(args)

    def move_package(self, task):
        package = pl.Path(task.meta['package'])
        package.rename(xml_gen_dir / package)
    
    def build(self):
        for targ in data_dirs:
            targ_fname = "_".join(targ.parts[-2:])
            yield {
                "basename" : "xml::schema.python",
                "name"     : targ_fname,
                "actions"  : [ CmdAction(self.glob_target), self.move_package ],
                "targets"  : [ xml_gen_dir / targ_fname ],
                "task_dep" : [ "_checkdir::xml" ],
                "meta"     : { "package" : targ_fname,
                               "focus" : targ }
            }

        for targ in rec_dirs:
            targ_fname = "rec_" + "_".join(targ.parts[-2:])
            yield {
                "basename" : "xml::schema.python.rec",
                "name"     : targ_fname,
                "actions"  : [ CmdAction(self.glob_rec_target), self.move_package ],
                "targets"  : [ xml_gen_dir / targ_fname ],
                "task_dep" : [ "_checkdir::xml" ],
                "meta"     : { "package" : targ_fname,
                               "focus" : targ }
            }

class XmlPythonSchema:

    def __init__(self):
        self.create_doit_tasks = self.build

class XmlSchemaVisualiseTask:

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        cmd = "xsdata"
        args = ["generate", "-o", "plantuml", "-pp", "{dependencies}", ">", "{targets}"]

        return {
            "basename" : "xml::schema.visual",
            "actions"  : [build_cmd(cmd, args)],
            "targets"  : ["schema.pu"],
            "file_dep" : ["schema.xsd"],
        }


class XmlValidateTask:

    def __init__(self):
        self.create_doit_tasks = self.build
        self.cmd               = "xml"
        self.args              = ["val",   # validate
                                  "-e",    # verbose errors
                                  "--net", # net access
                                  "--xsd"] # xsd schema
        self.targets           = []

    def validate(self, schema):
        return build_cmd(self.cmd, self.args)

    def build(self):
        return {
            "basename" : "xml::validate",
            "actions" : [self.validate],
            "targets" : self.targets,
            "params" : [ { "name" : "schema",
                           "short" : "s",
                           "type" : str,
                           "default" : "" }
                        ]
        }


class XmlFormatTask:
    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        cmd = "xml"
        args = ["fo", # format
                "-s", "4", # indent 4 spaces
                "-R", # Recover
                "-N", # remove redundant declarations
                "-e", "utf-8", # encode in utf-8
                "?",
                ">",
                "formatted"]

        # "--html"

        return {
            "basename" : "xml::format",
            "actions" : [],
            "targets" : []
        }
