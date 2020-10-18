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
                                     epilog = "\n".join(["Generate wordcloud from counts"]))
    parser.add_argument('--target', action="append")
    parser.add_argument('--output', default=None)

    args = parser.parse_args()
    args.target = [abspath(expanduser(x)) for x in args.target]
    if args.output is not None:
        args.output = abspath(expanduser(args.output))

    text = []
    target_queue = args.target
    while bool(target_queue):
        current = target_queue.pop(0)
        if isfile(current):
            with open(current,'r') as f:
                text += [x for x in f.readlines() if x[0] != "*"]
        else:
            target_queue += [join(current, x) for x in listdir(current)]

    makeImage(getFrequencyDictForText(text))
