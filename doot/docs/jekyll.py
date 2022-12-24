
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files
from time import strftime

import yaml
from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.files.clean_dirs import clean_target_dirs
from doot.builders.jekyll import jekyll_src

try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml

##-- end imports

##-- data
data_path      = files("doot.__templates")
post_template  = data_path / "jekyll_post"
index_template = data_path / "jekyll_tag_index"
tag_template   = data_path / "jekyll_tagfile"
##-- end data

##-- toml data
default_template = data_toml.tool.doot.jekyll.genpost.default_template
date_format      = data_toml.tool.doot.jekyll.genpost.date_format.strip()
title_format     = data_toml.tool.doot.jekyll.genpost.title_format.strip()
ext_format       = data_toml.tool.doot.jekyll.genpost.ext.strip()

##-- end toml data

__all__ = ["GenPostTask", "GenTagsTask"]


##-- directories
posts_dir = jekyll_src / "_posts"
tags_dir  = jekyll_src / "_generated" / "tags"
tag_index = jekyll_src / "tags" / "index.md"

jekyll_check_posts = CheckDir(paths=[posts_dir,
                                     tags_dir
                                     ],
                              name="jekyll.posts",
                              task_dep=["_checkdir::jekyll"])
##-- end directories

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


class GenPostTask:
    """ create a new post,
    using a template or the default in doot.__templates.jekyll_post

    has cli params of title and template

    """
    def __init__(self, template=None):
        self.create_doit_tasks = self.build
        self.template = pl.Path(template or post_template)

    def make_post(self, title, template):
        if template != "default":
            template = pl.Path(template)
        else:
            template = self.template

        post_path = posts_dir / (title_format
                                 .format_map({ "date"  : strftime(date_format),
                                              "title" : title.strip().replace(" ","_"),
                                              "ext"   : ext_format}))

        post_text = (template
                     .read_text()
                     .format_map({ "date"  : strftime(date_format),
                                   "title" : title.strip(),
                                   "ext"   : ext_format}))

        post_path.write_text(post_text)


    def build(self) -> dict:
        task_desc = {
            "basename" : "jekyll::post",
            "actions"  : [ self.make_post ],
            "targets"  : [ ],
            "task_dep" : ["_checkdir::jekyll.posts"],
            "params" : [
                { "name" : "title",
                 "long" : "title",
                 "short" : "t",
                 "type" : str,
                 "default" : "unnamed"
                },
                { "name"    : "template",
                  "long"    : "template",
                 "type"    : str,
                 "default" : default_template,
                }
            ]
        }
        return task_desc

    def gen_toml(self):
        """
        Generate a stub toml section used to customize this task
        """
        return """
##-- doot.jekyll
[tool.doot.jekyll.genpost]
ext = "md"
# used in datetime.strftime
date_format = "%Y-%m-%d"
# title_format.format_map({date, title, ext })
title_format = "{date}{title}.{ext}"
# 'default' for doot.__template.jekyll_post, else a path:
# can be overriden on cli
default_template = "default"

##-- end doot.jekyll
        """


class GenTagsTask:
    """
    Generate summary files for all tags used in md files in the jekyll src dir
    """
    # TODO make globber
    def __init__(self, template=None, index=None):
        self.create_doit_tasks = self.build
        self.tagset            = set()
        self.template          = pl.Path(template or tag_template)
        self.index             = pl.Path(index or index_template)


    def get_tags(self):
        for path in jekyll_src.glob("**/*.md"):
            data = load_yaml_data(path)
            if 'tags' in data and data['tags'] is not None:
                self.tagset.update([x.strip() for x in data['tags'].split(" ")])


    def make_tag_pages(self):
        tag_text = self.template.read_text()
        for tag in self.tagSet:
            tag_file = tags_dir / f"{tag}.md"
            formatted = tag_text.format_map({"tag" : tag})
            tag_file.write_text(formatted)

    def make_tag_index(self):
        if tag_index.exists():
            return

        tag_index.write_text(self.index.read_text())


    def build(self):
        return {
            "basename" : "jekyll::tag",
            "actions"  : [self.get_tags, self.make_tag_pages, self.make_tag_index ],
            "task_dep" : [ "_checkdir::jekyll.posts" ],
            "targets"  : [ tag_index ],
            "clean"    : [ clean_target_dirs ],
        }
