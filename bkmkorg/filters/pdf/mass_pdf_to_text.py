"""
Simple Utility to convert pdf library to text
"""
import argparse
# Setup root_logger:
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from subprocess import call

from bkmkorg.utils.bibtex import bibtex as BU
from bkmkorg.utils.pdf import pdf as PU
from bkmkorg.utils.file import retrieval

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))
parser.add_argument('-l', '--library')
##############################

if __name__ == "__main__":
    args = parser.parse_args()
    files = retrieval.get_data_files(args.library, ".pdf")
    PU.convert_pdfs_to_text(files)
