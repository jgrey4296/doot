#!~/anaconda/envs/bookmark/bin/python

"""
Using frequency - from: https://github.com/amueller/word_cloud
===============

Using a dictionary of word frequency.
"""

import argparse
import os
import re
from os import listdir, path
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from wordcloud import WordCloud

#--
from bkmkorg.utils import bibtex as BU
from bkmkorg.utils import retrieval

# Setup root_logger:
from os.path import splitext, split
import logging as root_logger
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
parser.add_argument('--target', action="append")
parser.add_argument('--output', default=None)


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

    text = []
    target_queue = retrieval.get_data_files(args.target, ".tags")
    while bool(target_queue):
        current = target_queue.pop(0)
        with open(current,'r') as f:
            text += [x for x in f.readlines() if x[0] != "*"]

    makeImage(getFrequencyDictForText(text))
