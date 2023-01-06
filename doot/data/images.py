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

##-- end imports
default_ocr_exts = [".GIF", ".JPG", ".PNG", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif"]

ocr_exts    : list[str] = doot.config.or_get(default_ocr_exts).tool.doot.images.ocr_exts()
batch_size  : int       = doot.config.or_get(20).tool.doot.batch_size()

def gen_toml(self):
    return "\n".join(["[tool.doot.images]",
                      f"ocr-exts = {default_ocr_exts}"
                      ])

class HashImages(globber.DirGlobber):
    """
    ([data] -> data) For each subdir, hash all the files in it
    info
    """
    gen_toml = gen_toml

    def __init__(self, dirs:DootLocData, roots=None, exts=None):
        super().__init__("images::hash", dirs, roots or [dirs.data], exts=exts)
        self.current_hashed = {}
        self.hash_record    = ".hashes"
        self.ext_check_fn = lambda x: x.is_file() and x.suffix in self.exts
        if not bool(self.exts):
            self.ext_check_fn = lambda x: x.is_file()

    def filter(self, fpath):
        is_cache = fpath != pl.Path() and fpath.name[0] in "._"
        if is_cache:
            return False

        for x in fpath.iterdir():
            if self.ext_check_fn(x):
                return True

        return False

    def subtask_detail(self, fpath, task):
        task.update({
            "targets" : [ fpath / self.hash_record ],
            "actions" : [ CmdAction(["touch", fpath / self.hash_record], shell=False),
                          (self.hash_remaining, [fpath]),
                         ],
            "clean"   : True,
        })
        return task

    def load_hashed(self, fpath):
        hash_file = fpath / self.hash_record
        hashes = [x.split(" ") for x in hash_file.read_text().split("\n") if bool(x)]
        self.current_hashed = {" ".join(xs[1:]).strip():xs[0] for xs in hashes}
        return hash_file

    def hash_remaining(self, fpath):
        print("Hashing: ", fpath)
        self.reset_batch_count()

        hash_file = self.load_hashed(fpath)
        dir_contents = [x for x in fpath.iterdir() if x.stem[0] != "."]

        while bool(dir_contents):
            batch        = [x for x in dir_contents[:batch_size] if str(x) not in self.current_hashed]
            dir_contents = dir_contents[batch_size:]

            if self.run_batch([batch, hash_file]):
                return


    def batch(self, data):
        act = CmdAction(["md5", "-r", *data[0]], shell=False)
        act.execute()
        with open(data[1], 'a') as f:
            f.write("\n" + act.out)


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
            txt_names      = [ fpath / f".{x.stem}.txt" for x in batch]
            filtered_batch = [ (x, y) for x,y in zip(batch, txt_names) if not y.exists() ]

            if self.run_batch(filtered_batch):
                return

    def batch(self, data):
        src, dst = data
        ocr_cmd    = CmdAction(["tesseract", src, dst.stem, "-l", "eng"], shell=False)
        mv_txt_cmd = CmdAction(["mv", dst.name, dst], shell=False)
        ocr_cmd.execute()
        mv_txt_cmd.execute()


