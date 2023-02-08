#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from typing import Final

from functools import partial
from itertools import cycle, chain
from doit.action import CmdAction

import doot
from doot import tasker, globber, task_mixins
from doot.taskslib.files import hashing

##-- end imports

import numpy as np
import PIL
from PIL import Image
from sklearn.cluster import KMeans

default_ocr_exts : Final = [".GIF", ".JPG", ".PNG", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".ppm"]

default_pdf_exts : Final = [".GIF", ".JPG", ".PNG", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".ppm"]

ocr_exts         : Final = doot.config.on_fail(default_ocr_exts, list).tool.doot.images.ocr_exts()
batch_size       : Final = doot.config.on_fail(20, int).tool.doot.batch.size()
ocr_out_ext      : Final = doot.config.on_fail(".ocr", str).tool.doot.images.ocr_out()

framerate        : Final = doot.config.on_fail(10, int).tool.doot.images.framerate()

THUMB            : Final = (200,200)

HashImages = hashing.HashAllFiles

def load_img(path:pl.Path):
    try:
        img = Image.open(str(path))
        img2 = img.convert('RGB')
        return img2
    except:
        return None

def norm_img(img):
    split_c1 = img.split()
    histograms = [np.array(x.histogram()) for x in split_c1]
    sums = [sum(x) for x in histograms]
    norm_c1 = [x/y for x,y in zip(histograms, sums)]
    return np.array(norm_c1).reshape((1,-1))

class OCRGlobber(globber.LazyGlobMixin, globber.DirGlobMixin, globber.DootEagerGlobber, task_mixins.BatchMixin, task_mixins.TargetedMixin):
    """
    ([data] -> data) Run tesseract on applicable files in each found directory
    to make dot txt files of ocr'd text from the image
    """

    def __init__(self, name="images::ocr", locs:DootLocData=None, roots=None, exts=ocr_exts, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=exts, rec=rec)
        assert(bool(self.exts))
        self.processed = dict()
        self.ext_check_fn = lambda x: x.is_file() and x.suffix in self.exts
        if not bool(self.exts):
            self.ext_check_fn = lambda x: x.is_file()

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        is_cache = fpath != pl.Path() and fpath.name[0] in "._"
        if is_cache:
            return self.control.reject

        for x in fpath.iterdir():
            if self.ext_check_fn(x):
                return self.control.accept

        return self.control.discard

    def task_detail(self, task, fpath=None):
        task.update({
            "actions" : [ self.ocr_all ],
            "clean"   : [ self.clean_all ],
        })
        return task

    def clean_all(self):
        chunks = self.target_chunks(base=globber.LazyGlobMixin)
        self.run_batches(*chunks, fn=self.clean_ocr_results)

    def clean_ocr_results(self, data):
        for name, fpath in data:
            for f in fpath.rglob(f".*{ocr_out_ext}"):
                f.unlink()

    def ocr_all(self):
        chunks  = self.target_chunks(base=globbed.LazyGlobMixin)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
            file_chunks = self.chunk((x for x in fpath.iterdir() if x.suffix in self.exts and not self.ocr_file_name(x).exists()))
            self.run_batches(*chunks, fn=self.batch_on_files)

    def batch_on_files(self, data):
        for src in data:
            dst        = self.get_ocr_file_name(src)
            ocr_cmd    = self.cmd("tesseract" src, dst.stem, "--psm", "1",  "-l", "eng")
            mv_txt_cmd = self.cmd("mv", dst.with_suffix(".txt").name, dst)
            ocr_cmd.execute()
            mv_txt_cmd.execute()

    def get_ocr_file_name(self, fpath):
        return fpath.parent / f".{fpath.stem}{ocr_out_ext}"

class Images2PDF(globber.LazyGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin, task_mixins.BatchMixin):
    """
    Combine globbed images into a single pdf file using imagemagick
    """

    def __init__(self, name="images::pdf", locs=None, roots=None, exts=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=exts or default_pdf_exts, rec=rec)
        assert(self.locs.build)
        assert(self.locs.temp)

    def set_params(self):
        return [
            { "name": "name", "short": "n", "type": str, "default": "collected"}
        ]

    def task_detail(self, task):
        task.update({
            "name"    : "build_single",
            "actions" : [
                self.find_and_process,,
                self.cmd(self.combine_pages)
            ],
            "targets" : [ self.locs.build / f"{self.args['name']}.pdf" ],
            "clean"   : [ (self.rmglob, [self.locs.build, f"{self.args['name']}.pdf"]) ],
        })
        return task

    def find_and_process(self):
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        chunks = self.chunk(globbed)
        self.run_batches(*chunks)

    def batch(self, data):
        batch_name = self.locs.temp / f"{root.stem}_{self.batch_count}.pdf"
        print(f"Batch {self.batch_count}: {batch_name}")
        args = ["magick", "convert"]
        args += [x[1] for x in data]
        args += ["-alpha", "off", batch_name]
        print(f"Batch Args: {args}")
        conversion = self.cmd(*args)
        conversion.execute()

    def combine_pages(self, targets):
        pages = [x for x in self.locs.temp.iterdir() if x.suffix == ".pdf"]
        return ["pdftk", *pages, "cat", "output", targets[0]]

class TODOImages2Video(globber.LazyGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    https://stackoverflow.com/questions/24961127/
    """

    def __init__(self, name="images::to.video", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=default_ocr_exts, rec=rec)
        assert(self.locs.temp)

    def task_detail(self, task, fpath):
        task.update({
            "actions" : [
                self.cmd(self.make_gif, fpath)
            ],
            "targets" : [self.locs.temp / f"{task['name']}.gif"]
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

class TODOPDF2Images(globber.LazyGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin, task_mixins.BatchMixin):
    """
    (src -> temp) Find pdfs and extract images for them for ocr
    """

    def __init__(self, name="image::from.pdf", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.src], rec=rec, exts=exts or [".pdf"])
        assert(self.locs.temp)

    def filter(self, fpath):
        return self.control.accept

    def task_detail(self, task, fpath):
        targ_dir = self.locs.temp / task['name']
        task.update({
            "actions"  : [
                (self.mkdirs, [targ_dir]),
                self.cmd(self.split_pdf, fpath, save="info"),
                (self.write_to, ["info", targ_dir / "info.txt"]),
            ],
            "targets" : [ targ_dir, targ_dir / "info.txt" ],
           "file_dep" : [ fpath ],
            "clean"   : [ (self.rmdirs, [ targ_dir ])],
        })
        return task

    def split_pdf(self, fpath, targets, task):
        cmd = [ "pdfimages", "-j", "-list"]
        cmd.append(fpath)
        cmd.append(pl.Path(targets[0]) / "page_")
        return cmd
