##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from itertools import cycle, chain
from doit.action import CmdAction
from doot import build_dir, data_toml, src_dir, gen_dir
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
rec_dirs  = [pl.Path(x) for x in data_toml.tool.doot.xml.recursive_dirs if pl.Path(x).exists()]

xml_gen_dir   = gen_dir
xml_build_dir = build_dir / "xml"
schema_dir    = xml_build_dir   / "schema"
elements_dir  = xml_build_dir   / "elements"
visual_dir    = xml_build_dir   / "visual"

##-- dir checks
xml_dir_check = CheckDir(paths=[xml_build_dir,
                                schema_dir,
                                elements_dir,
                                visual_dir,
                                ], name="xml", task_dep=["_checkdir::build"])

##-- end dir checks

def gen_toml():
    return """"
##-- doot.xml
[tool.doot.xml]
data_dirs      = ["pack/__data/core/xml"]
recursive_dirs = ["pack/__data/core/xml"]
##-- end doot.xml
"""



class XmlElementsTask:
    def __init__(self):
        self.create_doit_tasks = self.build
        self.cmd = "xml el -u"

    def generate_on_target(self, targets, task):
        if task.meta['recursive']:
            globbed = pl.Path(task.meta['focus']).glob("*.xml")
        elif task.meta['focus'].is_dir():
            globbed = pl.Path(task.meta['focus']).rglob("*.xml")
        else:
            globbed = [task.meta['focus']]

        xmls = " ".join(f"'{x}'" for x in globbed)
        return f"{self.cmd} {xmls}" + " > {targets}"


    def build(self):
        for targ, rec in chain(zip(data_dirs, cycle([False])),
                               zip(rec_dirs,  cycle([True]))):
            targ_fname = ("rec_" if rec else "") + "_".join(targ.with_suffix(".elements").parts[-2:])
            yield {
                "basename" : "xml::elements",
                "name"     : pl.Path(targ_fname).stem,
                "actions"  : [ CmdAction(self.generate_on_target)],
                "targets"  : [ elements_dir / targ_fname ],
                "task_dep" : ["_checkdir::xml"],
                "meta"     : { "focus" : targ,
                               "recursive" : rec,
                              },
                "clean"    : True
            }

    def gen_toml(self):
        return """
##-- doot.xml
[tool.doot.xml]
data_dirs      = ["pack/__data/core/xml"]
recursive_dirs = ["pack/__data/core/xml"]
##-- end doot.xml
"""


class XmlSchemaTask:
    """
    Generate .xsd's from directories of xml files
    """
    def __init__(self):
        self.create_doit_tasks = self.build
        self.cmd               = "trang"

    def generate_on_target(self, targets, task):
        if task.meta['recursive']:
            globbed = pl.Path(task.meta['focus']).glob("*.xml")
        elif task.meta['focus'].is_dir():
            globbed = pl.Path(task.meta['focus']).rglob("*.xml")
        else:
            globbed = [task.meta['focus']]

        xmls = " ".join(f"'{x}'" for x in globbed)
        return f"{self.cmd} {xmls}" + " {targets}"


    def build(self):
        for targ, rec in chain(zip(data_dirs, cycle([False])),
                               zip(rec_dirs, cycle([True]))):
            targ_fname = ("rec_" if rec else "") + "_".join((targ / "trang").with_suffix(".xsd").parts[-3:])
            yield {
                "basename" : "xml::schema",
                "name"     : pl.Path(targ_fname).stem,
                "actions"  : [ CmdAction(self.generate_on_target)],
                "targets"  : [ schema_dir / targ_fname ],
                "task_dep" : ["_checkdir::xml"],
                "meta"     : { "focus" : targ, "recursive" : rec },
                "clean"    : True,
                "uptodate" : [True],
            }



class XmlPythonSchemaRaw:
    """ Generate Python Dataclass bindings based on draw XML data  """
    def __init__(self):
        self.create_doit_tasks = self.build
        self.cmd = "xsdata"

    def get_args(self, task):
        args = ["generate",
                ("--recursive" if task.meta['recursive'] else ""),
                "-p", task.meta['package'], # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                str(task.meta['focus']) ]

        return args

    def generate_on_target(self, task):
        return f"{self.cmd} " + " ".join(self.get_args(task))

    def move_package(self, task):
        package = pl.Path(task.meta['package'])
        package.rename(xml_gen_dir / package)
    
    def build(self):
        for targ, rec in chain(zip(data_dirs, cycle([False])),
                               zip(rec_dirs, cycle([True]))):
            targ_fname = ("rec_raw_" if rec else "raw_") + "_".join(targ.parts[-2:])
            yield {
                "basename" : "xml::schema.python.raw",
                "name"     : targ_fname,
                "actions"  : [ CmdAction(self.generate_on_target), self.move_package ],
                "targets"  : [ xml_gen_dir / targ_fname ],
                "task_dep" : [ "_xsdata::config", "_checkdir::xml" ],
                "meta"     : { "package"   : targ_fname,
                               "focus"     : targ,
                               "recursive" : rec,
                              }
                # TODO clean gen dir
            }




class XmlPythonSchemaXSD:
    """ Generate python dataclass bindings from XSD's  """

    def __init__(self):
        self.create_doit_tasks = self.build
        self.cmd = "xsdata"

    def get_args(self, task):
        args = ["generate",
                ("--recursive" if task.meta['recursive'] else ""),
                "-p", task.meta['package'], # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                str(task.meta['focus']) ]

        return args

    def generate_on_target(self, task):
        return f"{self.cmd} " + " ".join(self.get_args(task))

    def move_package(self, task):
        package = pl.Path(task.meta['package'])
        package.rename(xml_gen_dir / package)

    def build(self):
        for targ, rec in chain(zip(data_dirs, cycle([False])),
                               zip(rec_dirs,  cycle([True]))):
            xsd_fname = ("rec_" if rec else "") + "_".join((targ / "trang").with_suffix(".xsd").parts[-3:])
            targ_fname = ("rec_xsd_" if rec else "xsd_") + "_".join(targ.parts[-2:])
            yield {
                "basename" : "xml::schema.python.xsd",
                "name"     : targ_fname,
                "actions"  : [ CmdAction(self.generate_on_target), self.move_package ],
                "targets"  : [ xml_gen_dir / targ_fname ],
                "file_dep" : [ schema_dir / xsd_fname ],
                "task_dep" : [ "_xsdata::config", "_checkdir::xml" ],
                "meta"     : { "package"   : targ_fname,
                               "focus"     : targ,
                               "recursive" : rec,
                              }
                # TODO clean gen dir
            }

class XmlSchemaVisualiseTask:

    def __init__(self):
        self.create_doit_tasks = self.build
        self.cmd = "xsdata"

    def get_args(self, task):
        args = ["generate",
                "-o", "plantuml", # output as plantuml
                "-pp",            # to stdout instead of make a file
                "{dependencies}", ">", "{targets}"]
        return args

    def generate_on_target(self, task):
        return f"{self.cmd} " + " ".join(self.get_args(task))


    def build(self):
        for targ, rec in chain(zip(data_dirs, cycle([False])),
                               zip(rec_dirs,  cycle([True]))):
            xsd_fname  = ("rec_" if rec else "") + "_".join((targ / "trang").with_suffix(".xsd").parts[-3:])
            targ_fname = ("rec_" if rec else "") + "_".join(targ.with_suffix(".plantuml").parts[-2:])
            pre_task   = "xml::schema:" + pl.Path(xsd_fname).stem
            yield {
                "basename" : "xml::schema.plantuml",
                "name"     : pl.Path(targ_fname).stem,
                "actions"  : [ CmdAction(self.generate_on_target) ],
                "targets"  : [ visual_dir / targ_fname ],
                "file_dep" : [ schema_dir / xsd_fname ],
                "task_dep" : [ "_xsdata::config",  "_checkdir::xml"],
                "meta"     : {},
                "clean"    : True,
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
        yield {
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

        yield {
            "basename" : "xml::format",
            "actions" : [],
            "targets" : []
        }
