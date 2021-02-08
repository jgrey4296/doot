"""
Find tweets missing from the main library
"""
# Setup root_logger:
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
from os.path import splitext, split
import logging as root_logger
import argparse

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU

##############################


if __name__ == "__main__":
    # Setup
    LOGLEVEL = root_logger.DEBUG
    LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
    root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

    console = root_logger.StreamHandler()
    console.setLevel(root_logger.INFO)
    root_logger.getLogger('').addHandler(console)
    logging = root_logger.getLogger(__name__)
    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join(["Compare two sets of twitter ids"]))
    parser.add_argument('-l', '--library')
    parser.add_argument('-s', '--source')
    parser.add_argument('-o', '--output')

    args = parser.parse_args()
    #args.aBool...
    args.library = abspath(expanduser(args.library))
    args.source = abspath(expanduser(args.source))
    args.output = abspath(expanduser(args.output))

    assert(isfile(args.library) and isfile(args.source))
    # Get the library ids
    library_set = set([])
    with open(args.library,'r') as f:
        library_set.update([x.strip() for x in f.readlines()])

    # Get the ids to check
    source_set = set([])
    source_dict = {}
    with open(args.source,'r') as f:
        pairs = [x.split(':') for x in f.readlines()]
        source_set.update([x[1].strip() for x in pairs])
        source_dict.update({x[1].strip(): x[0].strip() for x in pairs})

    missing_set = source_set - library_set

    logging.info("Library Size: {}".format(len(library_set)))
    logging.info("Source Size : {}".format(len(source_set)))
    logging.info("Missing Size: {}".format(len(missing_set)))

    with open(args.output, 'w') as f:
        for x in missing_set:
            f.write("http://twitter.com/{}/status/{}\n".format(source_dict[x], x))
