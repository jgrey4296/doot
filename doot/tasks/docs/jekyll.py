
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from importlib.resources import files
from time import strftime

import doot
from doot import globber
from doot.tasker import DootTasker

##-- end imports

##-- data
data_path      = files("doot.__templates.jekyll")
post_template  = data_path / "jekyll_post"
##-- end data

##-- toml data
default_template = doot.config.on_fail(post_template).jekyll.genpost.default_template(wrapper=pl.Path)
date_format      = doot.config.on_fail("%Y-%m-%d").jekyll.genpost.date_format.strip()
title_format     = doot.config.on_fail("{date}-{title}{ext}").jekyll.genpost.title_format.strip()
ext_format       = doot.config.on_fail(".md").jekyll.genpost.ext.strip()

##-- end toml data

__all__ = ["GenPostTask", "GenTagsTask"]


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

    def __init__(self, name="web::post", locs=None, template=None):
        super().__init__(name, locs)
        self.template  = pl.Path(template or post_template)
        self.locs.ensure("posts", task=name)

    def set_params(self):
        return [
            { "name"   : "template", "long"   : "template", "type"    : str, "default" : default_template}
        ]

    def task_detail(self, task) -> dict:
        task.update({
            "actions" : [ self.make_post ],
            "pos_arg" : "pos"
        })
        return task

    def make_post(self, pos):
        title    = " ".join(pos).strip()
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
