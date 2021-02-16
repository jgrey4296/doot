#!/usr/bin/env python3
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir

from subprocess import call
from pdfrw import PdfReader, PdfWriter, PageMerge
from pdfrw import IndirectPdfDict

import logging as root_logger
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
    count = 0
    if func is None:
        func = get2
    if isdir(output):
        output = join(output, "summary")

    writer = PdfWriter()

    for path in paths:
        try:
            pdf_obj = PdfReader(path)
            writer.addpage(func(pdf_obj))
        except:
            logging.warning("Error Encountered with {}".format(path))

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
    subprocess.run(['mutool',
                    'convert',
                    '-F', 'text',
                    '-o', join(output_dir, target),
                    source],
                   stdout=subprocess.PIPE)
