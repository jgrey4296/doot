##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from time import strftime
import yaml
##-- end imports

target_directory = "_posts"
file_format      = "md"
time_format      = "%Y-%m-%d"
time_str         = strftime(time_format)
title            = ""
tags             = ""
file_name = "{}-{}.{}".format(time_str, title.replace(" ","_"), file_format)

class GenPostTask:
    def __init__(self, *paths, data=None, **kwargs):
        self.create_doit_tasks = self.build
        self.args              = [pl.Path(x) for x in paths]
        self.kwargs            = kwargs

    def uptodate(self):
        return all([x.exists() for x in self.args])

    def mkdir(self):
        for x in self.args:
            try:
                x.mkdir(parents=True)
            except FileExistsError:
                print(f"{x} already exists")
                pass

    def build(self) -> dict:
        task_desc = self.kwargs.copy()
        task_desc.update({
            "actions"  : [ self.mkdir ],
            "targets"  : self.args,
            "uptodate" : [ self.uptodate ],
            "clean"    : [ force_clean_targets],
        })
        return task_desc


class GenTagsTask:

    def __init__(self):
        load_dir = "_posts"
        save_dir = "tags"

    def build(self):
        # load all post -> build tag pages -> write index file
        return {

        }

    def load_yaml_data(filename):
        """ Load a specified file, parse it as yaml """
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

    def load_all_posts(dir_name):
        logging.info("Loading all Posts in {}".format(dir_name))
        files = listdir(dir_name)
        loadedData = [load_yaml_data(join(dir_name,f)) for f in files if splitext(f)[1] == ".md"]
        tagSet = set([t for x in loadedData for t in x['tags'].split(" ")])
        return tagSet

    def make_tag_pages(tagSet):
        logging.info("Making Tag Pages: {}".format(tagSet))
        for tag in tagSet:
            write_yaml_tag_file(save_dir,tag)

    def write_yaml_tag_file(dir,tag):
        logging.info('Creating Tag File: {}'.format(tag))
        # use tagfile template
        with open(join(dir,"{}.md".format(tag)),'w') as f:
            f.write('---\n')
            f.write('layout: tag\n')
            f.write('title: {}\n'.format(tag))
            f.write('tag: {}\n'.format(tag))
            f.write('permalink: /tags/{}/\n'.format(tag))
            f.write('sitemap: false\n')
            f.write('---\n')


    def write_index_file(dir_name):
        # load __configs.jekyll_tag_template
        with open(join(dir_name, "index.html"), 'w') as f:
            f.write(index_str)
