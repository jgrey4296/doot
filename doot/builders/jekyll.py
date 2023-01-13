
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files

from doit.tools import LongRunning
from doit.action import CmdAction

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.clean_dirs import clean_target_dirs
from doot.utils.cmdtask import CmdTask
from doot.utils.tasker import DootTasker

##-- end imports


__all__ = [
    "task_jekyll_serve", "task_jekyll_build",
    "task_init_jekyll", "task_jekyll_install"
]


def task_jekyll_serve():
    def serve():
        cmd = ["bundle", "exec", "jekyll", "serve"]
        return cmd

    # jekyll serve
    return {
        "actions" : [LongRunning(serve, shell=False)],
        "file_dep" : ["jekyll.toml" , "Gemfile"],
        "task_dep" : ["jekyll::build"],
        "basename" : "jekyll::serve"
    }



class JekyllBuild(DootTasker):
    """
    Build the jekyll site, from the source destination,
    into the build destination
    using jekyll.toml
    """

    def __init__(self, name="jekyll::build", dirs=None):
        super().__init__(name, dirs)
        self.jekyll_config = self.dirs.root / "jekyll.toml"

    def set_params(self):
        return [
            { "name" : "drafts",
              "long" : "drafts",
              "type" : bool,
              "default" : False,
             }
        ]

    def task_detail(self, task):
        task.update({
            "actions"  : [
                self.copy_data,
                self.copy_src,
                CmdAction(self.cmd_builder, shell=False)
            ],
            "file_dep" : [ self.jekyll_config ],
            "uptodate" : [False],
        })
        return task

    def copy_data(self):
        shutil.copytree(str(self.dirs.data), str(self.dirs.temp), dirs_exist_ok=True)

    def copy_src(self):
        shutil.copytree(str(self.dirs.src), str(self.dirs.temp), dirs_exist_ok=True)

    def cmd_builder(self, drafts):
        cmd = [ "jekyll", "build", "--config", self.jekyll_config ]
        if drafts:
            cmd.append("--drafts")

        return cmd



def task_jekyll_install():
    """
    install the dependencies of jekyll,
    and create an initial config file

    # TODO add uptodate for if jekyll is installed
    """
    return {
        "basename" : "jekyll::install",
        "actions" : [CmdAction(["brew", "install", "chruby", "ruby-install", "xz"], shell=False),
                     CmdAction(["ruby-install", "ruby"], shell=False),
                     CmdAction(["chruby", "ruby-3.1.2"], shell=False),
                     CmdAction(["gem", "install", "jekyll", "tomlrb"], shell=False),
                     CmdAction(["bundle", "init"], shell=False),
                     CmdAction(["bundle", "add", "jekyll"], shell=False),
                     CmdAction(["bundle", "add", "jekyll-sitemap"], shell=False),
                     ],
        "clean"   : True,
    }

