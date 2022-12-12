##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
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

def task_xml_install():
    pass

def task_xml_structure():
    pass

def task_xml_schema():
    cmd = "trang"
    args = ["{file_dep}", "{targets}"]
    return {
        "actions"  : [build_cmd(cmd, args)],
        "targets"  : ["schema.xsd"],
        "file_dep" : [],
    }

def task_xml_schema_visualise():
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


def task_xml_elements():
    return {
        "actions" : ["xml el -u {targets}"],
        "targets" : [],
    }


def task_xml_format():
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
