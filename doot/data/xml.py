##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
import shlex

from itertools import cycle, chain
from doit.action import CmdAction
from doit.tools import Interactive
from doot import build_dir, data_toml, src_dir, gen_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber

##-- end imports
# https://relaxng.org/jclark/
# xmlschema, xsdata, xsdata-plantuml, generateDS
# http://www.davekuhlman.org/generateDS.html
# https://pyxb.sourceforge.net/
# https://xmlschema.readthedocs.io/en/latest/
# https://github.com/tefra/xsdata-plantuml
# https://python-jsonschema.readthedocs.io/en/stable/

data_dirs = [pl.Path(x) for x in data_toml.tool.doot.xml.data_dirs if pl.Path(x).exists()]

xml_gen_dir   = gen_dir
xml_build_dir = build_dir     / "xml"
schema_dir    = xml_build_dir / "schema"
elements_dir  = xml_build_dir / "elements"
visual_dir    = xml_build_dir / "visual"

##-- dir checks
xml_dir_check = CheckDir(paths=[xml_build_dir,
                                schema_dir,
                                elements_dir,
                                visual_dir,
                                ], name="xml", task_dep=["_checkdir::build"])

##-- end dir checks


class XmlElementsTask(globber.DirGlobber):
    """
    xml element retrieval using xml starlet toolkit
    http://xmlstar.sourceforge.net/
    """
    def __init__(self, targets=data_dirs):
        super(XmlElementsTask, self).__init__("xml::elements", [".xml"], targets, rec=True)
        self.cmd = "xml el -u"

    def subtask_detail(self, fname, task:dict) -> dict:
        task.update({"targets" : [elements_dir / (task['name'] + ".elements")],
                     "task_dep": ["_checkdir::xml"],
                     "clean"   : True})
        task['meta'].update({"focus" : fname })
        return task

    def generate_on_target(self, targets, task):
        focus_is_dir = task.meta['focus'].is_dir()
        if not self.rec and focus_is_dir:
            # dir glob wasn't recursive, so the task is
            globbed = pl.Path(task.meta['focus']).rglob("*.xml")
        elif focus_is_dir:
            # dir glob was recursive, so task isn't
            globbed = pl.Path(task.meta['focus']).glob("*.xml")
        else:
            # not a dir
            globbed = [task.meta['focus']]

        xmls = " ".join(shlex.quote(str(x)) for x in globbed)
        return f"{self.cmd} {xmls}" + " > {targets}"

    def subtask_actions(self, fname):
        return [CmdAction(self.generate_on_target)]


    def gen_toml(self):
        return """
##-- doot.xml
[tool.doot.xml]
data_dirs      = ["pack/__data/core/xml"]
recursive_dirs = ["pack/__data/core/xml"]
##-- end doot.xml
"""


class XmlSchemaTask(globber.DirGlobber):
    """
    Generate .xsd's from directories of xml files using trang
    https://relaxng.org/jclark/
    """
    def __init__(self, targets=data_dirs):
        super().__init__("xml::schema", [], targets)
        self.cmd = "trang"

    def generate_on_target(self, targets, task):
        focus_is_dir = task.meta['focus'].is_dir()
        if self.rec and focus_is_dir:
            globbed = task.meta['focus'].glob(f"*.xml")
        elif focus_is_dir:
            globbed = task.meta['focus'].rglob(f"*.xml")
        else:
            globbed = [task.meta['focus']]

        xmls = " ".join(shlex.quote(str(x)) for x in globbed)
        return f"{self.cmd} {xmls}" + " {targets}"

    def subtask_actions(self, fpath):
        return [CmdAction(self.generate_on_target)]

    def subtask_detail(self, fpath, task):
        task.update({
            "targets"  : [ schema_dir / (task['name'] + ".xsd") ],
            "task_dep" : ["_checkdir::xml"],
            "clean"    : True,
            "uptodate" : [True]})
        task['meta'].update({"focus" : fpath })
        return task

class XmlPythonSchemaRaw(globber.DirGlobber):
    """
    Generate Python Dataclass bindings based on raw XML data
    """

    def __init__(self, targets=data_dirs, rec=True):
        super().__init__("xml::schema.python.raw", [".xml"], targets, rec=rec)

    def generate_on_target(self, task):
        args = ["generate",
                ("--recursive" if not self.rec else ""),
                "-p", task.meta['package'] , # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                shlex.quote(str(task.meta['focus'])),
                ]
        return f"xsdata " + " ".join(args)

    def subtask_actions(self, fpath):
        return [ CmdAction(self.generate_on_target) ]

    def subtask_detail(self, fpath, task):
        gen_package = str(xml_gen_dir / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config", "_checkdir::xml" ],
            })
        task["meta"].update({"focus" : fpath,
                             "package" : gen_package,
                             })
        return task




class XmlPythonSchemaXSD(globber.FileGlobberMulti):
    """
    Generate python dataclass bindings from XSD's
    """

    def __init__(self, targets=data_dirs, rec=False):
        targets = data_dirs[:] + [ schema_dir ]
        super().__init__("xml::schema.python.xsd", [".xsd"], targets, rec=rec)


    def generate_on_target(self, task):
        args = ["generate",
                ("--recursive" if not self.rec else ""),
                "-p", task.meta['package'] , # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                shlex.quote(str(task.meta['focus'])),
                ]

        return f"xsdata " + " ".join(args)

    def subtask_actions(self, fpath):
        return [ CmdAction(self.generate_on_target)  ]

    def subtask_detail(self, fpath, task):
        gen_package = str(xml_gen_dir / task['name'])
        task.update({
                "targets"  : [ gen_package ],
                "file_dep" : [ fpath ],
                "task_dep" : [ "_xsdata::config", "_checkdir::xml" ],
            })
        task['meta'].update({ "focus"     : fpath,
                              "package" : gen_package
                             })
        return task

class XmlSchemaVisualiseTask(globber.FileGlobberMulti):
    """
    Generate Plantuml files ready for plantuml to generate images
    """

    def __init__(self, targets=data_dirs, rec=True):
        targets_plus = targets[:] + [ schema_dir ]
        super().__init__("xml::schema.plantuml", [".xsd"], targets_plus, rec=rec)


    def generate_on_target(self, task):
        cmd = [ "xsdata",
                 "generate",
                "-o", "plantuml", # output as plantuml
                "-pp",            # to stdout instead of make a file
                "{dependencies}", ">", "{targets}"]

        return " ".join(cmd)

    def subtask_actions(self, fpath):
        return [ CmdAction(self.generate_on_target) ]

    def subtask_detail(self, fpath, task):
        task.update({
            "actions"  : [ CmdAction(self.generate_on_target) ],
            "targets"  : [ visual_dir / (task['name'] + ".plantuml") ],
            "file_dep" : [ fpath ],
            "task_dep" : [ "_xsdata::config",  "_checkdir::xml"],
            "clean"    : True,
        })
        return task


class XmlValidateTask(globber.DirGlobber):
    """
    Validate xml's by schemas
    """

    def __init__(self, targets=data_dirs, rec=False, xsd=None):
        super().__init__("xml::validate", [], targets, rec=rec)
        self.args              = ["-e",    # verbose errors
                                  "--net", # net access
                                  "--xsd"] # xsd schema
        self.xsd = xsd
        if self.xsd is None:
            raise Exception("For Xml Validation you need to specify an xsd to validate against")

    def subtask_actions(self, fpath):
        if self.rec:
            xmls = fpath.glob("*.xml")
        else:
            xmls = fpath.rglob("*.xml")

        args = self.args + [ self.xsd ] + list(shlex.quote(str(xmls)))
        return [ CmdAction(f"xml val " + " ".join(args)) ]

    def subtask_detail(self, fpath, task):
        task.update({

        })
        return task



class XmlFormatTask(globber.DirGlobber):
    """
    Basic Formatting with backup
    """

    def __init__(self, targets=data_dirs, rec=True):
        super().__init__("xml::format", [".xml", ".xhtml", ".html"], data_dirs, rec=rec)
        self.args = ["-s", "4", # indent 4 spaces
                     "-R", # Recover
                     "-N", # remove redundant declarations
                     "-e", "utf-8", # encode in utf-8
                     ]
        # "--html"

    def format_xmls(self, task):
        ext_strs    = [f"*{ext}" for ext in self.exts]
        globbed     = {x for ext in ext_strs for x in task.meta['focus'].rglob(ext)}
        format_cmds = []

        for target in globbed:
            target_q   = shlex.quote(str(target))
            new_fmt    = shlex.quote(str(target.with_name(f"{target.name}.format")))
            fmt_backup = shlex.quote(str(target.with_name(f"{target.name}.backup")))

            fmt_cmd = ["xml", "fo"
                       , *self.args
                       , ("--html" if target.suffix in [".html", ".xhtml"] else "")
                       , target_q , ">" , new_fmt , ";"
                       , "mv" , "--verbose", "--update",  new_fmt, target_q
                       ]
            format_cmds.append(" ".join(fmt_cmd))

        return "; ".join(format_cmds)

    def subtask_actions(self, fpath):
        ext_strs = [f"*{ext}" for ext in self.exts]

        find_names  = " -o ".join(f"-name \"{ext}\"" for ext in ext_strs)
        depth = ""
        if self.rec:
            depth = "-maxdepth 1"

        backup_cmd = f"find {fpath} {depth} {find_names} | xargs -I %s cp --verbose --no-clobber %s %s.backup"
        total_cmds = [ CmdAction(backup_cmd), CmdAction(self.format_xmls) ]
        return total_cmds

    def subtask_detail(self, fpath, task):
        task.update({
            "uptodate" : [False],
            })
        task['meta'].update({ "focus" : fpath })
        return task
