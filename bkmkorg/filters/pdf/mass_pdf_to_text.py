"""
Simple Utility to convert pdf library to text
"""
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
from subprocess import call
import argparse

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU
from bkmkorg.utils import pdf as PU

# Setup root_logger:
import logging as root_logger

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join([""]))
    parser.add_argument('-l', '--library')

    args = parser.parse_args()
    files = retrieval.get_data_files(args.library, ".pdf")
    PU.convert_pdfs_to_text(files)
