#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from functools import partial
from itertools import cycle, chain
from doit.action import CmdAction
from doot import build_dir, data_toml, src_dir, gen_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber

##-- end imports

data_dirs        = [pl.Path(x) for x in data_toml.or_get([]).tool.doot.images.data_dirs() if pl.Path(x).exists()]
exts : list[str] = data_toml.or_get([".jpg"]).tool.doot.images.exts()
images_build_dir = build_dir / "images"

##-- dir checks
images_dir_check = CheckDir(paths=[images_build_dir,],
                          name="images",
                          task_dep=["_checkdir::build"])

##-- end dir checks

class ImagesListingTask:
    """
    Create a listing of all files needed to hash
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        foci = data_dirs
        return {
            "basename" : "_images::listing",
            "actions"  : [ CmdAction(self.list_files), CmdAction(self.clean_listing)],
            "targets"  : [ images_build_dir / "1_images.listing",
                           images_build_dir / "2_unique.listing"],
            "task_dep" : [ "_checkdir::images" ],
            "meta"     : { "exts"      : exts,
                           "foci"      : foci,
                          },
            "uptodate" : [False],
            "clean"    : True
        }

    def list_files(self, task, targets):
        output    = pl.Path(targets[0])
        focus     = task.meta['foci']
        exts_args = " -o ".join(f"-name '*{x}'" for x in task.meta['exts'])
        cmds = ["echo [Listing Images]"]
        if output.exists():
            output.unlink()

        for focus in task.meta['foci']:
            cmd = f"find {focus} -type f " + exts_args
            cmd += f" >> {output}"
            cmds.append(cmd)


        return "; ".join(cmds)

    def clean_listing(self, targets):
        in_f  = targets[0]
        out_f = targets[1]
        res = f"sort {in_f} | uniq > {out_f}"
        return f"echo [Removing Duplicate Paths]; " + res


    def gen_toml(self):
        return """
##-- doot.images
[tool.doot.images]
data_dirs      = [""]
recursive_dirs = [""]
exts           = [".jpg", ".jpeg", ".png", ".mp4"]

##-- end doot.images
"""
class ImagesHashTask:
    """
    Find all images, hash them,
    and identify duplicates

    # TODO sort duplicates by .stat().st_mtime
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        yield {
            "basename" : "images::md5",
            "actions"  : [ CmdAction(self.ignore_already_processed),
                           CmdAction(self.hash_all),
                           CmdAction(self.extract_duplicates)],
            "targets"  : [images_build_dir / "5_images.md5",
                          images_build_dir / "6_duplicates.md5"],
            "file_dep" : [ images_build_dir / "2_unique.listing" ],
            "meta"     : {
                "done" : images_build_dir / "3_processed.listing",
                "todo" : images_build_dir / "4_todo_hash.listing",
                },
            "clean"    : [self.clean_intermediates],
            "uptodate" : [False],
        }


    def ignore_already_processed(self, targets, task):
        if not pl.Path(targets[0]).exists():
            # if nothing has been done, everything is a todo
            return "cat {dependencies} > " + str(task.meta['todo'])

        # Get all files with a hash already
        prep_cmd   = f"cat {targets[0]} | gsed -E 's/^.+? //'"
        save_done  =  " > " + str(task.meta['done']) + ";"
        # Get all files *without* a hash already
        cat_listings = "cat {dependencies} " + str(task.meta['done'])
        filter_cmd   = " | sort | uniq -u"
        save_todo    = " > " + str(task.meta['todo'])
        return " ".join([prep_cmd, save_done,
                         cat_listings, filter_cmd, save_todo])

    def hash_all(self, targets, task):
        return " ".join(["cat", str(task.meta['todo']),
                         "| xargs md5 -r", f">> {targets[0]}"])

    def extract_duplicates(self, targets, task):
        sort_md5s = f"sort {targets[0]}"
        only_uniq = "| uniq --check-chars=32 --all-repeated=separate"
        save_to   = f"> {targets[1]}"
        return " ".join([sort_md5s, only_uniq, save_to])


    def clean_intermediates(self, task, targets):
        pl.Path(targets[1]).unlink(missing_ok=True)
        task.meta['todo'].unlink(missing_ok=True)
        task.meta['done'].unlink(missing_ok=True)
