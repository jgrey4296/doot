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
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber

##-- end imports

exts : list[str] = doot.config.or_get([".jpg"]).tool.doot.images.exts()

class HashImages(globber.DirGlobber):
    """
    For each subdir, hash all the files in it
    info
    """
    def __init__(self, dirs:DootLocData, roots=None, exts=exts):
        roots = roots or [pl.Path()]
        super().__init__("images::hash", dirs, roots, exts=exts)
        self.current_hashed = {}
        self.hash_record    = ".hashes"

    def filter(self, fpath):
        return fpath != pl.Path() and fpath.name[0] not in "._"

    def setup_detail(self, task):
        """ create a .hashes file to record hashes in each directory """
        actions = []
        for root in self.roots:
            actions += [CmdAction(["touch", fpath / self.hash_record], shell=False) for fpath in root.iterdir() if fpath.is_dir()]
        task.update({"actions" : actions})
        return task

    def subtask_detail(self, fpath, task):
        return task

    def subtask_actions(self, fpath):
        return [partial(self.hash_remaining, fpath)]

    def load_hashed(self, fpath):
        hash_file = fpath / self.hash_record
        hashes = [x.split(" ") for x in hash_file.read_text().split("\n") if bool(x)]
        self.current_hashed = {" ".join(xs[1:]).strip():xs[0] for xs in hashes}
        return hash_file

    def hash_remaining(self, fpath):
        print("Hashing: ", fpath)
        hash_file = self.load_hashed(fpath)
        dir_contents = [x for x in fpath.iterdir() if x.stem[0] != "."]
        batch_count = 0

        while bool(dir_contents):
            batch = [x for x in dir_contents[:10] if str(x) not in self.current_hashed]
            print(f"Batch Count: {batch_count} (size: {len(batch)})")
            dir_contents = dir_contents[10:]
            if not bool(batch):
                continue

            act = CmdAction(["md5", "-r", *batch], shell=False, save_out=True)
            act.execute()
            with open(hash_file, 'a') as f:
                f.write("\n")
                f.write(act.out)

            batch_count += 1




class TesseractGlobber(globber.DirGlobber):
    """
    Run tesseract on applicable files in each found directory
    to make dot txt files of ocr'd text from the image
    """
    file_types : ClassVar[list] = [".GIF", ".JPG", ".PNG", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif",]

    def __init__(self, dirs:DootLocData, roots=None):
        roots = roots or [pl.Path()]
        super().__init__("tesseract::go", dirs, roots, exts=TesseractGlobber.file_types)
        self.processed = dict()

    def filter(self, fpath):
        exts = {x.suffix for x in fpath.iterdir()}
        not_cache = fpath != pl.Path() and fpath.name[0] not in "._"
        return any(x in self.exts for x in exts) and not_cache

    def load_processed(self):
        self.processed = {x[1]:x[0] for ln in pl.Path("all_checksums").read_text().split("\n") for xs in ln.split(" ") }

    def setup_detail(self, task):
        task.update({
            # "actions" : [ self.load_processed ]
        })
        return task

    def subtask_actions(self, fpath):
        dir_contents = [x for x in fpath.iterdir() if x.suffix in self.exts]
        cmds = []

        for img in dir_contents:
            text_path = img.parent / f".{img.stem}.txt"
            if text_path.exists():
                continue

            text_cmd   = ["tesseract", img, text_path.stem, "-l", "eng"]
            mv_txt_cmd = ["mv", text_path.name, text_path]
            # pdf_cmd    = f"tesseract {pq(img)} {pq(text_path.stem)} -l eng pdf"
            cmds.append(CmdAction(text_cmd, shell=False))
            cmds.append(CmdAction(mv_txt_cmd, shell=False))

        return cmds

    def subtask_detail(self, fpath, task):
        task.update({})
        return task
