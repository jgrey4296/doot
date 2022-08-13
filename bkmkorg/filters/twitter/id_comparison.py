"""
Find tweets missing from the main library
"""
##-- imports
import argparse
import logging as root_logger

import pathlib as pl
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
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

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Compare two sets of twitter ids"]))
parser.add_argument('-l', '--library', required=True)
parser.add_argument('-s', '--source', required=True)
parser.add_argument('-o', '--output', required=True)
##-- end argparse



if __name__ == "__main__":
    args = parser.parse_args()
    args.library = pl.Path(args.library).expanduser().resolve()
    args.source  = pl.Path(args.source).expanduser().resolve()
    args.output  = pl.Path(args.output).expanduser().resolve()

    assert(args.library.is_file() and args.source.is_file())
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
