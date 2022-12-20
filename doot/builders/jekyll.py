
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files

from doit.tools import LongRunning
from doit.action import CmdAction
from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.files.clean_dirs import clean_target_dirs
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml

##-- end imports

##-- data

data_path = files("doot.__templates")
config_file = data_path.joinpath("jekyll_config")
config_text = config_file.read_text()
##-- end data

__all__ = [
    "jekyll_check_build", "jekyll_check_src",
    "task_jekyll_serve", "task_jekyll_build",
    "task_init_jekyll", "task_jekyll_install"
]

##-- checkdir
jekyll_config = pl.Path("jekyll.toml")
jekyll_toml   = None
jekyll_src    = pl.Path("docs/site")
jekyll_dest   = build_dir / "jekyll"

if jekyll_config.exists():
    jekyll_toml  = toml.load("jekyll.toml")
    jekyll_src  = pl.Path(jekyll_toml['source'])
    jekyll_dest = pl.Path(jekyll_toml['destination'])


jekyll_check_build = CheckDir(paths=[jekyll_dest,
                                     jekyll_src,
                                     ],
                              name="jekyll",
                              task_dep=["_checkdir::build"])

##-- end checkdir


def task_jekyll_serve():
    def serve():
        cmd = "bundle exec jekyll serve"
        return cmd

    # jekyll serve
    return {
        "actions" : [LongRunning(serve)],
        "file_dep" : ["jekyll.toml" , "Gemfile"],
        "task_dep" : ["jekyll::build"],
        "basename" : "jekyll::serve"
    }


def task_jekyll_build():
    """
    Build the jekyll site, from the source destination,
    into the build destination
    using jekyll.toml
    """
    def builder(drafts):
        cmd = "bundle exec jekyll build --config jekyl.toml"
        if drafts:
            cmd += " --drafts"

        return cmd

    return {
        "basename"    : "jekyll::build",
        "actions" : [ "bundle update", CmdAction(builder) ],
        "file_dep" : ["jekyll.toml"],
        "task_dep" : ["_checkdir::jekyll", "jekyll::install"],
        "targets"  : [ ".jekyll-cache"],
        "clean"    : [ clean_target_dirs ],
        "params" : [
            { "name" : "drafts",
              "long" : "drafts",
              "type" : bool,
              "default" : False,
            }
        ],
    }


def task_init_jekyll():
    """
    init a new jekyll project if it doesnt exist,
    in the config's src path
    """
    duplicate_config = jekyll_src / "_config.yml"

    return {
        "basename" : "jekyll::init",
        "actions" : [f"jekyll new {jekyll_src}",
                     f"rm {duplicate_config}",
                     ],
        "file_dep" : ["jekyll.toml"],
    }



def task_jekyll_install():
    """
    install the dependencies of jekyll,
    and create an initial config file
    """
    def create_jekyll_config(targets):
        with open(targets[0], 'w') as f:
            f.write(config_text)

    # TODO add uptodate for if jekyll is installed
    return {
        "basename" : "jekyll::install",
        "actions" : ["brew install chruby ruby-install xz",
                     "ruby-install ruby",
                     "chruby ruby-3.1.2",
                     "gem install jekyll tomlrb",
                     "bundle init",
                     "bundle add jekyll",
                     "bundle add jekyll-sitemap",
                     create_jekyll_config,
                     ],
        "targets" : ["jekyll.toml"],
        "clean"   : True,
    }

