##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
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

xml_dir      = build_dir / "xml"
schema_dir   = build_xml / "schema"
elements_dir = build_xml / "elements"
visual_dir   = build_xml / "visual"

class XmlPythonSchema:

    def __init__(self):
        self.create_doit_tasks = self.build


    def build():
        cmd = "xsdata"
        args = ["generate",
                "-r", # recursive
                "-p", "{targets}", # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                "{file_dep}"]
        return {
            "actions"  : [build_cmd(cmd, args)],
            "targets"  : ["out_package"],
            "file_dep" : ["schema.xsd"], # xml, json, xsd
        }

class XmlSchemaTask:
    """
    Generate xml schema for directories of xml files
    """
    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        cmd = "trang"
        args = ["{file_dep}", "{targets}"]
        return {
            "actions"  : [build_cmd(cmd, args)],
            "targets"  : ["schema.xsd"],
            "file_dep" : [],
        }



class XmlSchemaVisualiseTask:

    def __init__(self):
        self.create_doit_tasks = self.build

    def build():
    cmd = "xsdata"
    args = ["generate", "-o", "plantuml", "-pp", "{filedep}", ">", "{targets}"]

    return {
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
        return build_cmd(self.cmd, self.args + )

    def build(self):
        return {
            "actions" : [self.validate],
            "targets" : self.targets,
            "params" : [ { "name" : "schema",
                           "short" : "s",
                           "type" : str,
                           "default" : "" }
                        ]
        }


class XmlElementsTask:
    def __init__(self):
        self.create_doit_tasks = self.build

    def build():
        return {
            "actions" : ["xml el -u {targets}"],
            "targets" : [],
        }

class XmlFormatTask:
    def __init__(self):
        self.create_doit_tasks = self.build

    def build():
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
            "actions" : [],
            "targets" : []
        }
