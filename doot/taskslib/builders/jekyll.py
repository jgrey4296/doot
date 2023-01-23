
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files

from doit.tools import LongRunning
from doit.action import CmdAction

import doot
from doot.utils.clean_actions import clean_target_dirs
from doot.tasker import DootTasker, ActionsMixin

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

class JekyllBuild(DootTasker, ActionsMixin):
    """
    Build the jekyll site, from the source destination,
    into the build destination
    using jekyll.toml
    """

    def __init__(self, name="jekyll::build", locs=None):
        super().__init__(name, locs)
        self.jekyll_config = self.locs.root / "jekyll.toml"

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
                (self.copy_to, [self.locs.temp, self.locs.data, self.locs.src]),
                self.cmd(self.cmd_builder),
            ],
            "file_dep" : [ self.jekyll_config ],
            "uptodate" : [False],
        })
        return task

    def cmd_builder(self):
        cmd = [ "jekyll", "build", "--config", self.jekyll_config ]
        if self.args['drafts']:
            cmd.append("--drafts")

        return cmd
