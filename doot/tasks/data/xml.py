##-- imports
"""
https://relaxng.org/jclark/
xmlschema, xsdata, xsdata-plantuml, generateDS
http://www.davekuhlman.org/generateDS.html
https://pyxb.sourceforge.net/
https://xmlschema.readthedocs.io/en/latest/
https://github.com/tefra/xsdata-plantuml
https://python-jsonschema.readthedocs.io/en/stable/
"""
from __future__ import annotations

import pathlib as pl
import shutil
import shlex
from functools import partial
from itertools import cycle

from itertools import cycle, chain
from doit.tools import Interactive

from doot import globber, tasker

##-- end imports

from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin

class XmlValidateTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([data]) Validate xml's by schemas
    """

    def __init__(self, name="xml::validate", locs:DootLocData=None, roots:list[pl.Path]=None, rec=False, xsd=None):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml", ".xhtml", ".htm"], rec=rec)
        self.xsd = xsd
        if self.xsd is None:
            raise Exception("For Xml Validation you need to specify an xsd to validate against")

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "actions" : [ self.make_cmd(self.validate, fpath)]
        })
        return task

    def validate(self, fpath):
        args = ["xml", "val",
                "-e",    # verbose errors
                "--net", # net access
                "--xsd"  # xsd schema
                ]
        args.append(self.xsd)
        args += self.glob_target(fpath, fn=lambda x: x.is_file())
        return args

class XmlFormatTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([data] -> data) Basic Formatting with backup
    """

    def __init__(self, name="xml::format", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml", ".xhtml", ".html"], rec=rec)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            'actions': [ (self.format_xmls, [fpath] )]
        })
        return task

    def format_xmls(self, fpath):
        globbed  = self.glob_target(fpath, fn=lambda x: x.is_file())
        for target in globbed:
            backup = btarget.with_suffix(f"{btarget.suffix}.backup")
            if not backup.exists():
                backup.write_text(btarget.read_text())

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
            cmd = self.make_cmd(args)
            cmd.execute()
            target.write_text(cmd.out)
