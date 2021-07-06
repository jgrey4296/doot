#!/opt/anaconda3/envs/bookmark/bin/python
# https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
import argparse
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.pdf import pdf as PU
from bkmkorg.utils.file import retrieval

# Setup root_logger:
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
                                    epilog = "\n".join([""]))
parser.add_argument('--target')
parser.add_argument('--output')
parser.add_argument('-g', '--grouped', action='store_true')
parser.add_argument('--bound', default=200)


if __name__ == "__main__":
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))

    if args.grouped:
        groups = listdir(args.target)
        for group in groups:
            pdfs_to_process = retrieval.get_data_files(join(args.target, group), ".pdf")
            logging.info("Summarising {}'s {} pdfs".format(group, len(pdfs_to_process)))
            PU.summarise_pdfs(pdfs_to_process,
                              output="{}_{}".format(args.output, group),
                              bound=args.bound)
    else:
        # Find all pdfs in subdir
        pdfs_to_process = retrieval.get_data_files(args.target, ".pdf")
        logging.info("Summarising {} pdfs".format(len(pdfs_to_process)))
        PU.summarise_pdfs(pdfs_to_process, output=args.output, bound=args.bound)

    # writer.trailer.Info = IndirectPdfDict(
    #     Title='your title goes here',
    #     Author='your name goes here',
    #     Subject='what is it all about?',
    #     Creator='some script goes here',
    # )
