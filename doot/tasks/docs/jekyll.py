
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files
from time import strftime
import yaml

import doot
from doot import globber
from doot.tasker import DootTasker

##-- end imports

##-- data
data_path      = files("doot.__templates")
post_template  = data_path / "jekyll_post"
index_template = data_path / "jekyll_tag_index"
tag_template   = data_path / "jekyll_tagfile"
##-- end data

##-- toml data
default_template = doot.config.jekyll.genpost.default_template
date_format      = doot.config.jekyll.genpost.date_format.strip()
title_format     = doot.config.jekyll.genpost.title_format.strip()
ext_format       = doot.config.jekyll.genpost.ext.strip()

##-- end toml data

__all__ = ["GenPostTask", "GenTagsTask"]

##-- yaml util
def load_yaml_data(filename):
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

##-- end yaml util

from doot.mixins.cleaning import CleanerMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin

class GenPostTask(DootTasker):
    """
    (-> posts) create a new post,
    using a template or the default in doot.__templates.jekyll_post

    has cli params of title and template

    """

    def __init__(self, name="jekyll::post", locs=None, template=None):
        super().__init__(name, locs)
        self.template  = pl.Path(template or post_template)
        self.locs.ensure("posts")

    def set_params(self):
        return [
            { "name"   : "title", "long"    : "title", "short"   : "t", "type"    : str, "default" : "unnamed"},
            { "name"   : "template", "long"   : "template", "type"    : str, "default" : default_template}
        ]

    def task_detail(self, task) -> dict:
        task.update({
            "actions"  : [ self.make_post ],
        })
        return task

    def make_post(self):
        title    = self.args['title']
        template = self.args['template']
        if template != "default":
            template = pl.Path(template)
        else:
            template = self.template

        post_path = self.locs.posts / (title_format
                                       .format_map({ "date"  : strftime(date_format),
                                                     "title" : title.strip().replace(" ","_"),
                                                     "ext"   : ext_format}))

        post_text = (template
                     .read_text()
                     .format_map({ "date"  : strftime(date_format),
                                   "title" : title.strip(),
                                   "ext"   : ext_format}))

        post_path.write_text(post_text)

class GenTagsTask(DootTasker, CleanerMixin):
    """
    ([src] -> [tags, tagsIndex]) Generate summary files for all tags used in md files in the jekyll src dir
    """

    def __init__(self, name="jekyll::tag", locs=None, roots=None, template=None, index=None):
        super().__init__(name, locs)
        self.tagset   = set()
        self.template = pl.Path(template or tag_template)
        self.index    = pl.Path(index or index_template)
        self.roots    = roots or [locs.src]
        self.locs.ensure("tags", "tagsIndex")

    def task_detail(self, task):
        task.update({
            "actions"  : [self.get_tags, self.make_tag_pages ],
            "teardown" : [self.make_tag_index],
            "clean"    : [ self.clean_target_dirs ],
        })
        return task

    def get_tags(self):
        for root in self.roots:
            for path in root.glob("**/*.md"):
                data = load_yaml_data(path)
                if 'tags' in data and data['tags'] is not None:
                    self.tagset.update([x.strip() for x in data['tags'].split(" ")])

    def make_tag_pages(self):
        tag_text = self.template.read_text()
        for tag in self.tagSet:
            tag_file  = self.locs.tags / f"{tag}.md"
            formatted = tag_text.format_map({"tag" : tag})
            tag_file.write_text(formatted)

    def make_tag_index(self):
        if self.locs.tagsIndex.exists():
            return

        tag_index.write_text(self.index.read_text())
