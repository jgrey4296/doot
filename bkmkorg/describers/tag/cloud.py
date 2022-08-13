#!/usr/bin/env python
"""
Using frequency - from: https://github.com/amueller/word_cloud
===============

Using a dictionary of word frequency.
"""
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
import os
import re
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

import pathlib as pl
import matplotlib.pyplot as plt
import numpy as np
from bkmkorg.utils import bibtex as BU
from bkmkorg.utils.tag.collection import TagFile
from PIL import Image
from wordcloud import WordCloud
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging


##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Generate wordcloud from tag counts files"]))
parser.add_argument('--target', action="append", required=True)
parser.add_argument('--output', required=True)
##-- end argparse


def getFrequencyDictForText(lines):
    tmpDict = {}

    # making dict for counting frequencies
    for line in lines:
        vals = line.split(":")
        if len(vals) < 2:
            continue
        try:
            tmpDict[vals[0].strip()] = int(vals[1])
        except IndexError as err:
            breakpoint()

    return tmpDict


def makeImage(text, output:None|pl.Path=None):
    wc = WordCloud(background_color="white",
                   max_words=500,
                   width=1280,
                   height=1280,
                   scale=1,
                   collocations=False,
                   )
    # generate word cloud
    wc.generate_from_frequencies(text)

    if output is not None:
        plt.savefig(str(output))
    # show
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.show()




if __name__ == "__main__":
    args = parser.parse_args()
    if args.output is not None:
        args.output = pl.Path(args.output).expanduser().resolve()

    tags = TagFile.builder(args.target)

    makeImage(tags.count, output=args.output)
