#!/usr/bin/env python
"""
Using frequency - from: https://github.com/amueller/word_cloud
===============

Using a dictionary of word frequency.
"""

import argparse
import logging as root_logger
import os
import re
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

import matplotlib.pyplot as plt
import numpy as np
from bkmkorg.utils import bibtex as BU
from bkmkorg.utils.tag.collection import TagFile
from PIL import Image
from wordcloud import WordCloud

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Generate wordcloud from tag counts files"]))
parser.add_argument('--target', action="append", required=True)
parser.add_argument('--output', required=True)


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


def makeImage(text, output=None):
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
        plt.savefig(output)
    # show
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.show()




if __name__ == "__main__":
    args = parser.parse_args()
    if args.output is not None:
        args.output = abspath(expanduser(args.output))

    tags = TagFile.builder(args.target)

    makeImage(tags.count, output=args.output)
