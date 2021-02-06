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

def get2(srcpages):
    """ Get Two Pages of a PDF """
    scale = 0.5
    merged = PageMerge()
    merged.addpage(srcpages.pages[0])
    merged.addpage(srcpages.pages[1])

    return merged.render()

def read_pdfs(paths, func=None, output="./pdf_summary.pdf"):
    writer = PdfWriter()

    for path in paths:
        pdf_ob = PdfReader(pdf)
        writer.addpages(func(pdf_obj))

    writer.write(output)

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
