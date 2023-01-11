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
ocr_out_ext : str       = doot.config.or_get(".ocr").tool.doot.images.ocr_out()

framerate   : int       = doot.config.or_get(10).tool.doot.images.framerate()

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


class Images2PDF(globber.LazyFileGlobber):
    """
    Combine globbed images into a single pdf file using imagemagick
    """

    def __init__(self, name="images::pdf", dirs=None, roots=None, exts=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=exts or default_pdf_exts, rec=rec)


    def params(self):
        return [
            { "name": "name", "short": "n", "type": str, "default": "collected"}
        ]

    def task_detail(self, task):
        task.update({
            "name"    : "build_single",
            "actions" : [CmdAction(self.combine_pages, shell=False)],
            "targets" : [ self.dirs.build / f"{self._params['name']}.pdf" ],
            "clean"   : [self.clean_temp_and_targets],
        })
        return task

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [(self.images_to_pages, [fpath])],
        })
        return task

    def clean_temp_and_targets(self, targets):
        pl.Path(targets[0]).unlink(missing_ok=True)
        for x in self.dirs.temp.iterdir():
            if x.is_file() and x.suffix == ".pdf":
                x.unlink(missing_ok=True)

    def images_to_pages(self, fpath):
        globbed = self.glob_target(fpath)
        chunks = self.chunk(globbed, batch_size)
        self.run_batch(*chunks, root=fpath)

    def batch(self, data, root=None):
        batch_name = f"{root.stem}_{self.batch_count}.pdf"
        print(f"Batch {self.batch_count}: {batch_name}")
        args = ["magick", "convert"] + data + ["-alpha", "off", self.dirs.temp / batch_name]
        print(f"Batch Args: {args}")
        conversion = CmdAction(args, shell=False)
        conversion.execute()

    def combine_pages(self, targets):
        pages = [x for x in self.dirs.temp.iterdir() if x.suffix == ".pdf"]
        return ["pdftk", *pages, "cat", "output", targets[0]]

class Images2Video(globber.LazyFileGlobber):
    """
    https://stackoverflow.com/questions/24961127/
    """

    def __init__(self, name="images::to.video", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=default_ocr_exts, rec=rec)


    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [CmdAction((self.make_gif, [fpath], {}), shell=False)],
            "targets" : [self.dirs.temp / f"{task['name']}.gif"]
        })
        return task

    def make_gif(self, fpath, targets):
        globbed = self.glob_target(fpath)
        args = ["ffmpeg",
            "-f", "image2",
            "-framerate", framerate,
            "-loop",
            ]
        # ffmpeg -framerate 10 -pattern_type glob -i '*.jpeg' -c:v libx264 -pix_fmt yuv420p out.mp4
        args += reverse(list(z for xs in zip(globbed, cycle(["-i"])) for z in xs))

        args.append(targets[0])
        raise NotImplementedError
