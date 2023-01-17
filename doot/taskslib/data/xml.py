##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
import shlex
from functools import partial
from itertools import cycle

from itertools import cycle, chain
from doit.tools import Interactive

from doot import globber
from doot import tasker

##-- end imports
# https://relaxng.org/jclark/
# xmlschema, xsdata, xsdata-plantuml, generateDS
# http://www.davekuhlman.org/generateDS.html
# https://pyxb.sourceforge.net/
# https://xmlschema.readthedocs.io/en/latest/
# https://github.com/tefra/xsdata-plantuml
# https://python-jsonschema.readthedocs.io/en/stable/

# TODO config get data dirs

def gen_toml(self):
    return "\n".join([])

class XmlElementsTask(globber.DirGlobber, tasker.DootActions):
    """
    ([data] -> elements) xml element retrieval using xml starlet toolkit
    http://xmlstar.sourceforge.net/
    """

    def __init__(self, name="xml::elements", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xml"], rec=rec)
        assert("elements" in self.dirs.extra)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None:dict) -> dict:
        task.update({"targets" : [ self.dirs.extra['elements'] / (task['name'] + ".elements")],
                     "clean"   : True,
                     "actions" : [ self.cmd(self.generate_on_target, [fpath], save="elements"),
                                   (self.write_to, [fpath, "elements"]),
                                  ]
                     })
        return task

    def generate_on_target(self, fpath, targets, task):
        """
        build an `xml el` command of all available xmls
        """
        globbed = self.glob_files(fapth)
        return ["xml", "el", "-u", *globbed]

class XmlSchemaTask(globber.DirGlobber, tasker.DootActions):
    """
    ([data] -> schema) Generate .xsd's from directories of xml files using trang
    https://relaxng.org/jclark/
    """
    def __init__(self, name="xml::schema", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xml"], rec=rec)
        assert("schema" in self.dirs.extra)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ self.dirs.extra['schema'] / (task['name'] + ".xsd") ],
            "clean"    : True,
            "uptodate" : [True],
            "actions"  : [self.cmd(self.generate_on_target, fpath)],
            })
        return task

    def generate_on_target(self, fpath, targets, task):
        globbed = self.glob_files(fpath)
        return ["trang", *globbed, *targets]

class XmlPythonSchemaRaw(globber.DirGlobber, tasker.DootActions):
    """
    ([data] -> codegen) Generate Python Dataclass bindings based on raw XML data
    """

    def __init__(self, name="xml::schema.python.raw", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xml"], rec=rec)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        gen_package = str(self.dirs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config"],
            "actions"  : [ self.cmd(self.generate_on_target, fpath, gen_package) ],
            })
        return task

    def generate_on_target(self, fpath, gen_package, task):
        args = ["xsdata", "generate",
                ("--recursive" if not self.rec else ""),
                "-p", gen_package,
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                fpath,
                ]
        return args

class XmlPythonSchemaXSD(globber.EagerFileGlobber, tasker.DootActions):
    """
    ([data] -> codegen) Generate python dataclass bindings from XSD's
    """

    def __init__(self, name="xml::schema.python.xsd", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xsd"], rec=rec)
        self.dirs.build = dirs.build

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        gen_package = str(self.dirs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "file_dep" : [ fpath ],
            "task_dep" : [ "_xsdata::config"],
            "actions" : [self.cmd(self.gen_target, fpath, gen_package) ],
            })
        return task

    def gen_target(self, fpath, gen_package, task):
        args = ["xsdata", "generate",
                ("--recursive" if not self.rec else ""),
                "-p", gen_package,
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                fpath,
                ]

        return args

class XmlSchemaVisualiseTask(globber.EagerFileGlobber, tasker.DootActions):
    """
    ([data] -> visual) Generate Plantuml files ready for plantuml to generate images
    """

    def __init__(self, name="xml::schema.plantuml", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xsd"], rec=rec)
        assert("visual" in dirs.extra)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ self.dirs.extra['visual'] / (task['name'] + ".plantuml") ],
            "file_dep" : [ fpath ],
            "task_dep" : [ "_xsdata::config" ],
            "actions" : [self.cmd([ "xsdata", "generate", "-o", "plantuml", "-pp", fpath], save="result")
                         (self.write_to, [fpath, "result"])
                         ],
            "clean"    : True,
            })
        return task

class XmlValidateTask(globber.DirGlobber, tasker.DootActions):
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
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "actions" : [ self.cmd(self.validate, fpath)]
                    })

    def validate(self, fpath):
        args = ["xml", "val",
                "-e",    # verbose errors
                "--net", # net access
                "--xsd"  # xsd schema
                ]
        args.append(self.xsd)
        args += self.glob_files(fpath)
        return args

class XmlFormatTask(globber.DirGlobber, tasker.DootActions):
    """
    ([data] -> data) Basic Formatting with backup
    TODO cleanup backups
    """

    def __init__(self, name="xml::format", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".xml", ".xhtml", ".html"], rec=rec)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({'actions': [ (self.format_xmls, [fpath] )]})
        return task

    def format_xmls(self, fpath):
        globbed  = self.glob_files(fpath)
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
            cmd = self.cmd(args)
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
