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
default_pdf_exts = [".GIF", ".JPG", ".PNG", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif"]

ocr_exts    : list[str] = doot.config.or_get(default_ocr_exts).tool.doot.images.ocr_exts()
batch_size  : int       = doot.config.or_get(20).tool.doot.batch_size()
ocr_out_ext : str = doot.config.or_get(".ocr").tool.doot.images.ocr_out()

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

    def __init__(self, name="images::ocr", dirs:DootLocData=None, roots=None, exts=ocr_exts, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=exts, rec=rec)
        assert(bool(self.exts))
        self.processed = dict()
        self.ext_check_fn = lambda x: x.is_file() and x.suffix in self.exts
        if not bool(self.exts):
            self.ext_check_fn = lambda x: x.is_file()

    def filter(self, fpath):
        is_cache = fpath != pl.Path() and fpath.name[0] in "._"
        if is_cache:
            return self.control.reject

        for x in fpath.iterdir():
            if self.ext_check_fn(x):
                return self.control.accept

        return self.control.discard

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [(self.ocr_remaining, [fpath])],
            "clean"   : [(self.clean_ocr_files, [fpath])],
        })
        return task

    def ocr_file_name(self, fpath):
        return fpath.parent / f".{fpath.stem}{ocr_out_ext}"

    def clean_ocr_files(self, fpath):
        for f in fpath.glob(f".*{ocr_out_ext}"):
            f.unlink()

    def ocr_remaining(self, fpath):
        chunks = self.chunk((x for x in fpath.iterdir() if x.suffix in self.exts and not self.ocr_file_name(x).exists()),
                            batch_size)

        self.run_batch(*chunks)

    def batch(self, data):
        for src in data:
            dst = self.ocr_file_name(src)
            ocr_cmd    = CmdAction(["tesseract", src, dst.stem, "-l", "eng"], shell=False)
            mv_txt_cmd = CmdAction(["mv", dst.with_suffix(".txt").name, dst], shell=False)
            ocr_cmd.execute()
            mv_txt_cmd.execute()



class ImagesPDF(globber.LazyFileGlobber):
    """
    Combine globbed images into a single pdf file using imagemagick and img2pdf
    """

    def __init__(self, name="images::pdf", dirs=None, roots=None, exts=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=exts or default_pdf_exts, rec=rec)

    def task_detail(self, task):
        task.update({
            "actions" : [CmdAction(self.combine_images, shell=False)],
            "targets" : [ self.dirs.build / f"{task['name']}.pdf" ],
            "clean"   : [self.clean_temp_and_targets],
        })
        return task

    def clean_temp_and_targets(self, targets):
        pl.Path(targets[0]).unlink()
        for x in self.dirs.temp.iter():
            if x.is_file() and x.suffix() == ".pdf":
                x.unlink()

    
    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [(self.images_to_pages, [fpath])],
        })
        return task

    def images_to_pages(self, fpath):
        globbed = self.glob_target(fpath)

        while bool(globbed):
            batch   = globbed[:batch_size]
            globbed = globbed[batch_size:]
            print("Remaining: {len(globbed)}")
            filtered_batch = [x for x in batch if not (self.dirs.temp / x.with_suffix(".pdf").name).exists() ]
            self.run_batch([filtered_batch, fpath])

    def batch(self, data):
        imgs, root = data
        batch_name = f"{root.stem}_{self.batch_count}.pdf"
        print("Batch {self.batch_count}: {batch_name}")
        conversion = CmdAction(["magick", "convert", *imgs, "-alpha", "off", self.dirs.temp / batch_name], shell=False)
        conversion.execute()

    def combine_pages(self, targets):
        pages = [x for x in self.dirs.temp.iterdir() if x.suffix == ".pdf"]
        return ["pdftk", *pages, "cat", "output", targets[0]]
