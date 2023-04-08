
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files

from doit.action import CmdAction

import doot
from doot.tasker import DootTasker

import logging as logmod
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

__all__ = [
    "task_jekyll_serve", "task_jekyll_build",
    "task_init_jekyll", "task_jekyll_install"
]

from doot.mixins.commander import CommanderMixin
from doot.mixins.cleaning import CleanerMixin
from doot.mixins.filer import FilerMixin
import yaml
from importlib.resources import files

data_path      = files("doot.__templates.jekyll")
index_template = data_path / "jekyll_tag_index"
tag_template   = data_path / "jekyll_tagfile"

def task_jekyll_install():
    """
    install the dependencies of jekyll,
    and create an initial config file

    # TODO add uptodate for if jekyll is installed
    """
    return {
        "basename" : "web::install",
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

class JekyllBuild(DootTasker, CommanderMixin, FilerMixin):
    """
    Build the jekyll site, from the source destination,
    into the build destination
    using jekyll.toml
    """

    def __init__(self, name="web::build", locs=None):
        super().__init__(name, locs)
        self.jekyll_config = self.locs.root / "jekyll.toml"
        self.locs.ensure("data", "site", "temp", "codegen", task=name)

    def is_current(self):
        return False

    def set_params(self):
        return [
            { "name" : "drafts", "long" : "drafts", "type" : bool, "default" : False }
        ]

    def task_detail(self, task):
        task.update({
            "actions"  : [
                self.make_cmd(self.cmd_builder),
            ],
            "file_dep" : [ self.jekyll_config ],
            "task_dep" : [ "web::tag" ],
        })
        return task

    def cmd_builder(self):
        cmd = [ "jekyll", "build", "--config", self.jekyll_config ]
        if self.args['drafts']:
            cmd.append("--drafts")

        return cmd

class JekyllServe(DootTasker, CommanderMixin):
    def __init__(self, name="web::serve", locs=None):
        super().__init__(name, locs)
        self.jekyll_config = self.locs.root / "jekyll.toml"

    def set_params(self):
        return [
            { "name" : "drafts", "short" : "D", "type": bool, "default": True, 'inverse': 'nodraft' },
            { "name" : "background", "long": "background", "short": "B", "type" : bool, "default": True, 'inverse': 'foreground' },
            ]

    def task_detail(self, task):
        cmd_args = ["jekyll", "serve", "--config", self.jekyll_config]
        # if self.args['background']:
        #     cmd_args.append("--detach")
        if self.args['drafts']:
            cmd_args.append("--drafts")

        task.update({
            "actions" : [
                self.make_cmd("open", "http://127.0.0.1:4000"),
                self.make_cmd(cmd_args),
            ],
            "task_dep": [
                "web::tag"
            ]
        })
        return task


class GenTagsTask(DootTasker, CleanerMixin):
    """
    ([src] -> [tags, tagsIndex]) Generate summary files for all tags used in md files in the jekyll src dir
    """

    def __init__(self, name="web::tag", locs=None, roots=None, template=None, index=None):
        super().__init__(name, locs)
        self.tagSet   = set()
        self.output   = self.locs.codegen
        self.template = pl.Path(template or tag_template)
        self.index    = pl.Path(index or index_template)
        self.roots    = roots or [locs.site]
        self.locs.ensure("tags", "tagsIndex", task=name)

    def task_detail(self, task):
        task.update({
            "actions"  : [self.get_tags, self.make_tag_pages, self.make_tag_index ],
            "target"   : [ self.output ],
            "clean"    : [ self.clean_target_dirs ],
        })
        return task

    def get_tags(self):
        for root in self.roots:
            for path in root.glob("**/*.md"):
                if path.is_relative_to(self.output):
                    continue
                data = self.load_yaml_data(path)
                if data:
                    self.tagSet.update([x.strip() for x in data.get('tags', [])])

    def make_tag_pages(self):
        tag_text = self.template.read_text()
        for tag in self.tagSet:
            tag_file  = self.locs.codegen / "tags" / f"{tag}.md"
            formatted = tag_text.format_map({"tag" : tag})
            tag_file.write_text(formatted)

    def make_tag_index(self):
        if self.locs.tagsIndex.exists():
            return

        tag_index.write_text(self.index.read_text())

    def load_yaml_data(self, filename:pl.Path):
        """ Load a specified file, parse it as yaml
        from https://stackoverflow.com/questions/25814568
        """
        logging.info("Loading Yaml For: {}".format(filename))
        with open(filename,'r') as f:
            count = 0;
            total = ""
            currLine = f.readline()
            while count < 2 and currLine is not None:
                if currLine == "---\n":
                    count += 1
                elif count == 1:
                    total += currLine
                    currLine = f.readline()

        return yaml.safe_load(total)
