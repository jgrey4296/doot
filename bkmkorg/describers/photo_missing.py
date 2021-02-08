"""
Script to find missing photos

"""
# IMPORTS
import logging as root_logger
from hashlib import sha256
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir, mkdir
from shutil import copy

# Setup root_logger:
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU
from bkmkorg.utils import hash_check

########################################
if __name__ == "__main__":
    logging.info("Starting Photo Description")
    import argparse

    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join(["Find and Hash images, revealing duplicates"]))
    parser.add_argument('-l', '--library', action="append")
    parser.add_argument('-t', '--target', action="append")
    parser.add_argument('-c', '--copy', action="store_true")
    parser.add_argument('-o', '--output')
    args = parser.parse_args()

    logging.info("Finding library images")
    library_images = retrieval.get_data_files(args.library, retrieval.img_and_video)
    logging.info("Finding target images")
    target_images = retrieval.get_data_files(args.target, retrieval.img_and_video)
    logging.info("Finding missing images")
    missing = hash_check.find_missing(library_images, target_images)
    logging.info("Found {} missing images".format(len(missing)))

    #write conflicts to an org file:
    if not args.copy:
        count = 0
        grouping = int(len(missing) / 100)
        with open(expanduser(args.output),'w') as f:
            f.write("* Missing\n")
            for i,x in enumerate(missing):
                if (i % grouping) == 0:
                    f.write("** Group {}\n".format(count))
                    count += 1

                f.write("   [[{}]]\n".format(x))


    # create a directory and copy files missing from the library in
    if args.copy:
        target_dir = splitext(expanduser(args.output))[0]
        if not exists(target_dir):
            mkdir(target_dir)

        for x in missing:
            path = split(x)
            parent = split(path[0])[1]

            if not exists(join(target_dir, parent)):
                mkdir(join(target_dir, parent))
            copy(x, join(target_dir, parent))
