#!/usr/bin/env python3

"""
Using frequency - from: https://github.com/amueller/word_cloud
===============

Using a dictionary of word frequency.
"""

import argparse
import numpy as np
import os
import re
from PIL import Image
from os import path
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU

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
    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join(["Generate wordcloud from tag counts files"]))
    parser.add_argument('--target', action="append")
    parser.add_argument('--output', default=None)

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
