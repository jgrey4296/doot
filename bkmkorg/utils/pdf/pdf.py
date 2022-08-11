#!/usr/bin/env python
##-- imports
import logging as root_logger
import subprocess
import unicodedata
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from subprocess import call, run
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import pypandoc as pandoc
from bkmkorg.utils.file.temp_dir import mk_temp, temp_dir
from pdfrw import IndirectPdfDict, PageMerge, PdfReader, PdfWriter
##-- end imports


logging = root_logger.getLogger(__name__)


def get2(srcpages):
    scale = 0.5
    srcpages = PageMerge() + srcpages.pages[:2]
    x_increment, y_increment = (scale * i for i in srcpages.xobj_box[2:])
    for i, page in enumerate(srcpages):
        page.scale(scale)
        page.x = 0 if i == 0 else x_increment
        page.y = 0

    return srcpages.render()


def summarise_pdfs(paths, func=None, output="./pdf_summary", bound=200):
    """
    For a list of pdfs, get the first two pages of each,
    and make a pdf of those
    """
    count = 0
    if func is None:
        func = get2
    if isdir(output):
        output = join(output, "summary")

    writer = PdfWriter()

    for path in paths:
        try:
            if splitext(path)[1] == ".pdf":
                pdf_obj = PdfReader(path)
                writer.addpage(func(pdf_obj))
            else:
                raise Exception()
        except:
            logging.warning("Error Encountered with {}".format(path))
            mk_temp()
            # from stackoverflow.com/questions/2365411
            if not path.isascii():
                path = unicodedata.normalize("NFKD", path).encode("ascii", "ignore")

            pandoc.convert_text(f"File: {path}", "pdf", outputfile=join(temp_dir, "temp.pdf"), format="md")
            pdf_obj = PdfReader(join(temp_dir, "temp.pdf"))
            writer.addpage(func(pdf_obj))


        if len(writer.pagearray) > bound:
            # if pdf is too big, create another
            writer.write("{}_{}.pdf".format(output, count))
            writer = PdfWriter()
            count += 1

    writer.write("{}_{}.pdf".format(output, count))

def convert_pdfs_to_text(files):
    logging.info("Converting {} files".format(len(files)))
    for x in files:
        path = split(x)[0]
        name = splitext(split(x)[1])[0]
        text_file = join(path,".{}.txt".format(name))
        if exists(text_file):
            continue

        call_sig = ['pdftotext', x, text_file]
        logging.info("Converting: {}".format(" ".join(call_sig)))
        call(call_sig)

def convert_alternative(source, output_dir, title):
    target = "{}.txt".format(title)
    logging.info("Converting {} from {}".format(target, source))
    run(['mutool',
         'convert',
         '-F', 'text',
         '-o', join(output_dir, target),
         source],
        stdout=subprocess.PIPE)


def merge_pdfs(paths, output="./pdf_summary"):
    writer = PdfWriter()

    for path in paths:
        try:
            logging.info("File : {}".format(split(path)[1]))
            pdf_obj = PdfReader(path)
            for x in pdf_obj.pages:
                writer.addpage(x)
        except:
            logging.warning("Error Encountered with {}".format(path))

    writer.write("{}.pdf".format(output))
