
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files

from doit.tools import LongRunning
from doit.action import CmdAction

import doot
from doot.files.checkdir import CheckDir
from doot.files.clean_dirs import clean_target_dirs
from doot.utils.cmdtask import CmdTask

##-- end imports

##-- data

data_path = files("doot.__templates")
config_file = data_path.joinpath("jekyll_config")
config_text = config_file.read_text()
##-- end data

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


def task_jekyll_build(jekyll_config:pl.Path):
    """
    Build the jekyll site, from the source destination,
    into the build destination
    using jekyll.toml
    """
    def builder(drafts):
        cmd = ["bundle", "exec", "jekyll", "build", "--config", jekyll_config)
        if drafts:
            cmd.append(" --drafts")

        return cmd

    return {
        "basename" : "jekyll::build",
        "actions"  : [ CmdAction(["bundle", "update"], shell=False), CmdAction(builder, shell=False) ],
        "file_dep" : [ jekyll_config ],
        "task_dep" : ["_checkdir::jekyll", "jekyll::install"],
        "targets"  : [ ".jekyll-cache"],
        "clean"    : [ clean_target_dirs ],
        "params"   : [
            { "name" : "drafts",
              "long" : "drafts",
              "type" : bool,
              "default" : False,
            }
        ],
    }


def task_init_jekyll(jekyll_config:pl.Path, dirs:DootLocData):
    """
    init a new jekyll project if it doesnt exist,
    in the config's src path
    """
    duplicate_config : pl.Path = dirs.src / "_config.yml"

    return {
        "basename" : "jekyll::init",
        "actions" : [CmdAction(["jekyll", "new", jekyll_src], shell=False),
                     lambda: duplicate_config.unlink(missing_ok=True),
                     ],
        "file_dep" : [jekyll_config],
    }



def task_jekyll_install(jekyll_config:pl.Path):
    """
    install the dependencies of jekyll,
    and create an initial config file

    # TODO add uptodate for if jekyll is installed
    """
    def create_jekyll_config(targets):
        pl.Path(targets[0]).write_text(config_text)

    return {
        "basename" : "jekyll::install",
        "actions" : [CmdAction(["brew", "install", "chruby", "ruby-install", "xz"], shell=False),
                     CmdAction(["ruby-install", "ruby"], shell=False),
                     CmdAction(["chruby", "ruby-3.1.2"], shell=False),
                     CmdAction(["gem", "install", "jekyll", "tomlrb"], shell=False),
                     CmdAction(["bundle", "init"], shell=False),
                     CmdAction(["bundle", "add", "jekyll"], shell=False),
                     CmdAction(["bundle", "add", "jekyll-sitemap"], shell=False),
                     create_jekyll_config,
                     ],
        "targets" : [ jekyll_config ],
        "clean"   : True,
    }

