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

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber
from doot.files import hash_all

##-- end imports
default_ocr_exts = [".GIF", ".JPG", ".PNG", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif"]

ocr_exts    : list[str] = doot.config.or_get(default_ocr_exts).tool.doot.images.ocr_exts()
batch_size  : int       = doot.config.or_get(20).tool.doot.batch_size()

def gen_toml(self):
    return "\n".join(["[tool.doot.images]",
                      f"ocr-exts = {default_ocr_exts}"
                      ])

HashImages = hash_all.HashAllFiles

class OCRGlobber(globber.DirGlobber):
    """
    ([data] -> data) Run tesseract on applicable files in each found directory
    to make dot txt files of ocr'd text from the image
    """
    gen_toml = gen_toml

    def __init__(self, dirs:DootLocData, roots=None, exts=ocr_exts):
        super().__init__("images::ocr", dirs, roots or [dirs.data], exts=exts)
        assert(bool(self.exts))
        self.processed = dict()
        self.ext_check_fn = lambda x: x.is_file() and x.suffix in self.exts
        if not bool(self.exts):
            self.ext_check_fn = lambda x: x.is_file()

    def filter(self, fpath):
        is_cache = fpath != pl.Path() and fpath.name[0] in "._"
        if is_cache:
            return False

        for x in fpath.iterdir():
            if not self.ext_check_fn(x):
                continue
            ocr_file = (fpath / f".{x.stem}.txt")
            if not ocr_file.exists():
                return True

        return False

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [(self.ocr_remaining, [fpath])]
        })
        return task

    def ocr_remaining(self, fpath):
        self.reset_batch_count()
        dir_contents = [x for x in fpath.iterdir() if x.suffix in self.exts]

        while bool(dir_contents):
            batch          = [ x for x in dir_contents[:batch_size] ]
            dir_contents   = dir_contents[batch_size:]
            print(f"Remaining: {len(dir_contents)}")
            txt_names      = [ fpath / f".{x.stem}.txt" for x in batch]
            filtered_batch = [ (x, y) for x,y in zip(batch, txt_names) if not y.exists() ]
            if not bool(filtered_batch):
                continue

            print(f"Batch Count: {self.batch_count} (size: {len(filtered_batch)})")
            if self.run_batch(filtered_batch):
                return

    def batch(self, data):
        for src,dst in data:
            ocr_cmd    = CmdAction(["tesseract", src, dst.stem, "-l", "eng"], shell=False)
            mv_txt_cmd = CmdAction(["mv", dst.name, dst], shell=False)
            ocr_cmd.execute()
            mv_txt_cmd.execute()
