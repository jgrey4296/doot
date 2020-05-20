"""
    Script to find missing photos

"""
##############################
# IMPORTS
####################
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
##############################
# CONSTANTS
####################
FILE_TYPES = [".gif",".jpg",".jpeg",".png",".mp4",".bmp", ".mov", ".avi", ".webp", ".tiff"]

##############################
# VARIABLES
####################
missing_types = set()
##############################
# Utilities
####################
def file_to_hash(filename):
    with open(filename, 'rb') as f:
        return sha256(f.read()).hexdigest()

##############################
# Core Functions
####################
def find_images(directories):
    found = []
    queue = directories[:]
    processed = set()
    while queue:
        current = queue.pop(0)
        if current in processed:
            continue
        else:
            processed.add(current)
        ftype = splitext(current)[1].lower()
        if isfile(current) and ftype in FILE_TYPES:
            found.append(current)

        elif isfile(current) and ftype not in FILE_TYPES and ftype not in missing_types:
            logging.warning("Unrecognized file type: {}".format(splitext(current)[1].lower()))
            missing_types.add(ftype)

        elif isdir(current):
            queue += [join(current,x) for x in listdir(current)]

    return found


def hash_all(images):
    hash_dict = {}
    conflicts = {}
    update_num = int(len(images) / 100)
    count = 0
    for i,x in enumerate(images):
        if i % update_num == 0:
            logging.info("{} / 100".format(count))
            count += 1
        the_hash = file_to_hash(x)
        if the_hash not in hash_dict:
            hash_dict[the_hash] = []
        hash_dict[the_hash].append(x)
        if len(hash_dict[the_hash]) > 1:
            conflicts[the_hash] = len(hash_dict[the_hash])

    return (hash_dict, conflicts)

def find_missing(library, others):
    library_hash, conflicts = hash_all(library)
    missing = []
    update_num = int(len(others) / 100)
    count = 0
    for i,x in enumerate(others):
        if i % update_num == 0:
            logging.info("{} / 100".format(count))
            count += 1
        the_hash = file_to_hash(x)
        if the_hash not in library_hash:
            missing.append(x)
    return missing

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
    args.target = [expanduser(x) for x in args.target]

    logging.info("Finding library images")
    library_images = find_images(args.library)
    logging.info("Finding target images")
    target_images = find_images(args.target)
    logging.info("Finding missing images")
    missing = find_missing(library_images, target_images)
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

    if args.copy:
        # create a directory and copy files in
        target_dir = splitext(expanduser(args.output))[0]
        if not exists(target_dir):
            mkdir(target_dir)

        current_group = 0
        grouping = int(len(missing) / 100)
        for i,x in enumerate(missing):
            if (i % grouping) == 0:
                current_group += 1
                next_dir = join(target_dir, "group_{}".format(str(current_group)))
                if not exists(next_dir):
                    mkdir(next_dir)
            copy(x, join(target_dir,
                             "group_{}".format(str(current_group))))
