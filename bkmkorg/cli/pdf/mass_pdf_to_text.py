"""
Simple Utility to convert pdf library to text
"""
##-- imports
from __future__ import annotations

import pathlib as pl
import argparse
import logging as root_logger
from subprocess import call

from bkmkorg.files import collect
from bkmkorg.pdf import manipulate as PU
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

##-- parser
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))
parser.add_argument('-l', '--library', required=True)
##-- end parser


##-- ifmain
if __name__ == "__main__":
    args = parser.parse_args()
    files = collect.get_data_files(args.library, ".pdf")
    PU.convert_pdfs_to_text(files)

##-- end ifmain
