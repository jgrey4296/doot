"""
Compare 2+ bibtex files, output number of entries missing from the largest bibtex

"""

from bibtexparser.bparser import BibTexParser
from os.path import splitext, expanduser, abspath, split
import argparse
import bibtexparser as b
# Setup root_logger:
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU

if __name__ == "__main__":
    console = root_logger.StreamHandler()
    console.setLevel(root_logger.INFO)
    root_logger.getLogger('').addHandler(console)
    logging = root_logger.getLogger(__name__)

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n".join(["Compare bibtex files, print out the keys missing from the first"]))
    parser.add_argument('-t', '--target', action='append')
    args = parser.parse_args()

    args.target = [abspath(expanduser(x)) for x in args.target]

    logging.info("Targeting: {}".format(args.target))

    # Get Bibtex files
    all_bib_paths = retrieval.get_data_files(args.targeet, ".bib")
    all_dbs = []
    for t in all_bib_paths:
        # Use a new parser for each so library isn't shared
        parser = BibTexParser(common_strings=False)
        parser.ignore_nonstandard_types = False
        parser.homogenise_fields = True

        with open(t, 'r') as f:
            db = b.load(f, parser)
            all_dbs.append(db)

    logging.info("DB Sizes: {}".format(", ".join([str(len(x.entries)) for x in all_dbs])))

    # Sort the bibtex's by their size
    sorted_dbs = sorted([(len(x.entries), x) for x in all_dbs], reverse=True)

    # Use the largest as Primary
    head = sorted_dbs[0][1]
    rst = sorted_dbs[1:]
    head_set = {x['ID'] for x in head.entries}
    missing_keys = set([])

    # For remaining, get entries that are missing
    for _, db in rst:
        db_set = {x['ID'] for x in db.entries}
        if head_set.issuperset(db_set):
            continue

        missing_keys.update(db_set.difference(head_set))

    logging.info("{} Keys missing from master: {}".format(len(missing_keys), "\n".join(missing_keys)))
