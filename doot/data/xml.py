##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
import shlex
from functools import partial
from itertools import cycle

from itertools import cycle, chain
from doit.action import CmdAction
from doit.tools import Interactive
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber

##-- end imports
# https://relaxng.org/jclark/
# xmlschema, xsdata, xsdata-plantuml, generateDS
# http://www.davekuhlman.org/generateDS.html
# https://pyxb.sourceforge.net/
# https://xmlschema.readthedocs.io/en/latest/
# https://github.com/tefra/xsdata-plantuml
# https://python-jsonschema.readthedocs.io/en/stable/

class XmlElementsTask(globber.DirGlobber):
    """
    ([data] -> elements) xml element retrieval using xml starlet toolkit
    http://xmlstar.sourceforge.net/
    """
    def __init__(self, dirs:DootLocData, roots:list[pl.Path]=None):
        super().__init__("xml::elements", dirs, roots or [dirs.data], exts=[".xml"], rec=True)
        assert("elements" in self.dirs.extra)

    def subtask_detail(self, fpath, task:dict) -> dict:
        task.update({"targets" : [ self.dirs.extra['elements'] / (task['name'] + ".elements")],
                     "clean"   : True})
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(partial(self.generate_on_target, fpath), shell=False, save_out=str(fpath))
                 partial(self.write_elements, fpath),
                ]

    def generate_on_target(self, fpath ,targets, task):
        """
        build an `xml el` command of all available xmls
        """
        focus_is_dir = fpath.is_dir()
        if not self.rec and focus_is_dir:
            # dir glob wasn't recursive, so the task is
            globbed = fpath.rglob("*.xml")
        elif focus_is_dir:
            # dir glob was recursive, so task isn't
            globbed = fpath.glob("*.xml")
        else:
            # not a dir
            globbed = [fpath]

        return ["xml", "el", "-u", *globbed]

    def write_elements(self, fpath, targets, task):
        result = task.values[str(fpath)]
        pl.Path(targets[0]).write_text(result)

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
    ([data] -> schema) Generate .xsd's from directories of xml files using trang
    https://relaxng.org/jclark/
    """
    def __init__(self, dirs:DootLocData, roots:list[pl.Path]=None):
        super().__init__("xml::schema", dirs, roots or [dirs.data], exts=[".xml"])
        assert("schema" in self.dirs.extra)

    def subtask_detail(self, fpath, task):
        task.update({
            "targets"  : [ self.dirs.extra['schema'] / (task['name'] + ".xsd") ],
            "clean"    : True,
            "uptodate" : [True]})
        return task

    def subtask_actions(self, fpath):
        return [CmdAction(partial(self.generate_on_target, fpath), shell=False)]

    def generate_on_target(self, fpath, targets, task):
        focus_is_dir = fpath.is_dir()
        if self.rec and focus_is_dir:
            globbed = fpath.glob(f"*.xml")
        elif focus_is_dir:
            globbed = fpath.rglob(f"*.xml")
        else:
            globbed = [fpath]

        return ["trang", *globbed, *targets]


class XmlPythonSchemaRaw(globber.DirGlobber):
    """
    ([data] -> codegen) Generate Python Dataclass bindings based on raw XML data
    """

    def __init__(self, dirs:DootLocData, roots:list[pl.Path]=None):
        super().__init__("xml::schema.python.raw", dirs, roots or [dirs.data], exts=[".xml"], rec=rec)

    def subtask_detail(self, fpath, task):
        gen_package = str(self.dirs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config"],
            })
        task["meta"].update({"package" : gen_package})
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(partial(self.generate_on_target, fpath), shell=False) ]

    def generate_on_target(self, fpath, task):
        args = ["xsdata", "generate",
                ("--recursive" if not self.rec else ""),
                "-p", task.meta['package'] , # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                fpath,
                ]
        return args


class XmlPythonSchemaXSD(globber.FileGlobberMulti):
    """
    ([data] -> codegen) Generate python dataclass bindings from XSD's
    """

    def __init__(self, dirs:DootLocData, roots:list[pl.Path]=None):
        super().__init__("xml::schema.python.xsd", dirs, roots or [dirs.data], exts=[".xsd"], rec=rec)
        self.dirs.build = dirs.build

    def subtask_detail(self, fpath, task):
        gen_package = str(self.dirs.codegen / task['name'])
        task.update({
                "targets"  : [ gen_package ],
                "file_dep" : [ fpath ],
                "task_dep" : [ "_xsdata::config"],
            })
        task['meta'].update({"package" : gen_package})
        return task

    def subtask_actions(self, fpath):
        return [CmdAction(partial(self.gen_target, fpath), shell=False)]

    def gen_target(self, fpath, task):
        args = ["xsdata", "generate",
                ("--recursive" if not self.rec else ""),
                "-p", task.meta['package'] , # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                fpath,
                ]

        return args

class XmlSchemaVisualiseTask(globber.FileGlobberMulti):
    """
    ([data] -> visual) Generate Plantuml files ready for plantuml to generate images
    """

    def __init__(self, dirs:DootLocData, roots:list[pl.Path]=None):
        super().__init__("xml::schema.plantuml", dirs, roots or [dirs.data], exts=[".xsd"], rec=rec)
        assert("visual" in dirs.extra)


    def subtask_detail(self, fpath, task):
        task.update({
            "targets"  : [ self.dirs.extra['visual'] / (task['name'] + ".plantuml") ],
            "file_dep" : [ fpath ],
            "task_dep" : [ "_xsdata::config" ],
            "clean"    : True,
        })
        return task


    def subtask_actions(self, fpath):
        gen_act = CmdAction([ "xsdata", "generate",
                              "-o", "plantuml", # output as plantuml
                              "-pp",            # to stdout instead of make a file
                              fpath
                             ],
                            shell=False, save_out=str(fpath))

        return [ gen_act, partial(self.save_uml, fpath) ]

    def save_uml(self, fpath, targets, task):
        result = task.values[str(fpath)]
        pl.Path(targets[0]).write_text(result)

class XmlValidateTask(globber.DirGlobber):
    """
    ([data]) Validate xml's by schemas
    """

    def __init__(self, dirs:DootLocData, roots:list[pl.Path]=None, rec=False, xsd=None):
        super().__init__("xml::validate", dirs, roots or [dirs.data], rec=rec)
        self.xsd = xsd
        if self.xsd is None:
            raise Exception("For Xml Validation you need to specify an xsd to validate against")

    def subtask_detail(self, fpath, task):
        task.update({})
        return task

    def subtask_actions(self, fpath):
        args = ["xml", "val",
                "-e",    # verbose errors
                "--net", # net access
                "--xsd"  # xsd schema
                ]
        args.append(self.xsd)

        if self.rec:
            args += list(fpath.glob("*.xml"))
        else:
            args += list(fpath.rglob("*.xml"))

        return [ CmdAction(args, shell=False) ]




class XmlFormatTask(globber.DirGlobber):
    """
    ([data] -> data) Basic Formatting with backup
    TODO cleanup backups
    """

    def __init__(self, dirs:DootLocData, roots:list[pl.Path]=None, rec=True):
        super().__init__("xml::format", dirs, roots or [dirs.data], exts=[".xml", ".xhtml", ".html"], rec=rec)

    def setup_detail(self, task):
        """
        Add the backup action to setup
        """
        task['actions' ] = [self.backup_xmls]
        return task

    def subtask_detail(self, fpath, task):
        task['meta'].update({ "focus" : fpath })
        return task

    def subtask_actions(self, fpath):
        globbed  = {x for ext in self.exts for x in fpath.rglob(f"*{ext}")}
        actions  = []

        for target in globbed:
            args = ["xml" , "fo",
                    "-s", "4",     # indent 4 spaces
                    "-R",          # Recover
                    "-N",          # remove redundant declarations
                    "-e", "utf-8", # encode in utf-8
                    ]
            if target.suffix in [".html", ".xhtml", ".htm"]:
                args.append("--html")

            args.append(target)
            # Format and save result:
            actions.append(CmdAction(args, shell=False, save_out=str(target)))
            # Write result to the file:
            actions.append(partial(self.write_formatting, target))

        return actions

    def backup_xmls(self):
        """
        Find all applicable files, and copy them
        """
        globbed  = {x for ext in ext_strs for root in self.roots for x in root.rglob(f"*{ext}")}

        for btarget in backup_targets:
            backup = btarget.with_suffix(f"{btarget.suffix}.backup")
            if backup.exists():
                continue
            backup.write_text(btarget.read_text())

    def write_formatting(self, target, task):
        formatted_text = task.values[str(target)]
        target.write_text(formatted_text)
