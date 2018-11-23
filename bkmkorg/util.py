import IPython
from os.path import isfile
import logging
from collections import namedtuple

bookmarkTuple = namedtuple("bookmark","name url tags")

def open_file(filename):
    logging.debug("Opening file: {}".format(filename))
    x = None
    with open(filename, 'r') as f:
        x = f.read()
    return x

def writeToFile(filename,data):
    logging.debug("Writing to file: {}".format(filename))
    if isfile(filename):
        raise Exception("Filename {} already exists".format(filename))
    with open(filename,'w') as f:
        f.write(data)
