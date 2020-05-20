"""
Verify a backup of a library is up to date

"""
import argparse
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
from filecmp import dircmp
from shutil import copy, copytree
# Setup root_logger:
from os.path import splitext, split
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

def copy_missing(the_cmp, exclude=None):
    if exclude is None:
        exclude = []
    queue = [the_cmp]

    while bool(queue):
        current = queue.pop(0)
        # Copy left_only to right
        for missing in current.left_only:
            logging.info("Missing: {} in {} from {}".format(missing, current.left, current.right))
            loc_l = join(current.left, missing)
            loc_r = join(current.right, missing)
            if isfile(loc_l) and splitext(missing)[1] not in exclude:
                copy(loc_l, loc_r)
            else:
                assert(isdir(loc_l))
                copytree(loc_l, loc_r)

        queue += current.subdirs.values()

if __name__ == "__main__":

    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join([""]))
    parser.add_argument('--library')
    parser.add_argument('--target')
    parser.add_argument('-e', '--exclude', action="append")

    args = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    args.target = abspath(expanduser(args.target))

    the_cmp = dircmp(args.library, args.target)

    copy_missing(the_cmp, exclude=args.exclude)
