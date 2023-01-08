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
from doot.utils.checkdir import CheckDir
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

def gen_toml(self):
    return "\n".join([])

class XmlElementsTask(globber.DirGlobber):
    """
    ([data] -> elements) xml element retrieval using xml starlet toolkit
    http://xmlstar.sourceforge.net/
    """

    def __init__(self, name="xml::elements", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xml"], rec=rec)
        assert("elements" in self.dirs.extra)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.accept
        return self.discard

    def subtask_detail(self, fpath, task:dict) -> dict:
        task.update({"targets" : [ self.dirs.extra['elements'] / (task['name'] + ".elements")],
                     "clean"   : True})
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction((self.generate_on_target, [fpath], {}), shell=False, save_out=str(fpath))
                 (self.write_elements, [fpath]),
                ]

    def generate_on_target(self, fpath ,targets, task):
        """
        build an `xml el` command of all available xmls
        """
        globbed = super(globber.DirGlobber, self).glob_target(fpath, fn=lambda x: True)
        return ["xml", "el", "-u", *globbed]

    def write_elements(self, fpath, targets, task):
        result = task.values[str(fpath)]
        pl.Path(targets[0]).write_text(result)



class XmlSchemaTask(globber.DirGlobber):
    """
    ([data] -> schema) Generate .xsd's from directories of xml files using trang
    https://relaxng.org/jclark/
    """
    def __init__(self, name="xml::schema", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xml"], rec=rec)
        assert("schema" in self.dirs.extra)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.accept
        return self.discard


    def subtask_detail(self, fpath, task):
        task.update({
            "targets"  : [ self.dirs.extra['schema'] / (task['name'] + ".xsd") ],
            "clean"    : True,
            "uptodate" : [True]})
        return task

    def subtask_actions(self, fpath):
        return [CmdAction((self.generate_on_target, [fpath], {}), shell=False)]

    def generate_on_target(self, fpath, targets, task):
        globbed = super(globber.DirGlobber, self).glob_target(fpath, fn=lambda x: True)
        return ["trang", *globbed, *targets]


class XmlPythonSchemaRaw(globber.DirGlobber):
    """
    ([data] -> codegen) Generate Python Dataclass bindings based on raw XML data
    """

    def __init__(self, name="xml::schema.python.raw", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xml"], rec=rec)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.accept
        return self.discard

    def subtask_detail(self, fpath, task):
        gen_package = str(self.dirs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config"],
            })
        task["meta"].update({"package" : gen_package})
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction((self.generate_on_target, [fpath], {}), shell=False) ]

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


class XmlPythonSchemaXSD(globber.EagerFileGlobber):
    """
    ([data] -> codegen) Generate python dataclass bindings from XSD's
    """

    def __init__(self, name="xml::schema.python.xsd", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xsd"], rec=rec)
        self.dirs.build = dirs.build

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.accept
        return self.discard

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
        return [CmdAction((self.gen_target, [fpath], {}), shell=False)]

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

class XmlSchemaVisualiseTask(globber.EagerFileGlobber):
    """
    ([data] -> visual) Generate Plantuml files ready for plantuml to generate images
    """

    def __init__(self, name="xml::schema.plantuml", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xsd"], rec=rec)
        assert("visual" in dirs.extra)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.accept
        return self.discard


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

        return [ gen_act, (self.save_uml, [fpath]) ]

    def save_uml(self, fpath, targets, task):
        result = task.values[str(fpath)]
        pl.Path(targets[0]).write_text(result)

class XmlValidateTask(globber.DirGlobber):
    """
    ([data]) Validate xml's by schemas
    """

    def __init__(self, name="xml::validate", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=False, xsd=None):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xml", ".xhtml", ".htm"], rec=rec)
        self.xsd = xsd
        if self.xsd is None:
            raise Exception("For Xml Validation you need to specify an xsd to validate against")

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.accept
        return self.discard

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
        args += super(globber.DirGlobber, self).glob_target(fpath, fn=lambda x: True)

        return [ CmdAction(args, shell=False) ]




class XmlFormatTask(globber.DirGlobber):
    """
    ([data] -> data) Basic Formatting with backup
    TODO cleanup backups
    """

    def __init__(self, name="xml::format", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xml", ".xhtml", ".html"], rec=rec)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.accept
        return self.discard

    def subtask_detail(self, fpath, task):
        task['meta'].update({ "focus" : fpath })
        return task

    def subtask_actions(self, fpath):
        return [ (self.format_xmls, [fpath] )]

    def format_xmls(self, fpath):
        globbed  = list(super(globber.DirGlobber, self).glob_target(fpath, fn=lambda x: True))

        self.backup_xmls(globbed)
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
            cmd = CmdAction(args, shell=False)
            cmd.execute()
            target.write_text(cmd.out)

    def backup_xmls(self, globbed):
        """
        Find all applicable files, and copy them
        """
        for btarget in globbed:
            backup = btarget.with_suffix(f"{btarget.suffix}.backup")
            if backup.exists():
                continue
            backup.write_text(btarget.read_text())

