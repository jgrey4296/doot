"""
    Photo Description Script

"""
##############################
# IMPORTS
####################
import logging as root_logger
from hashlib import sha256
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir

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
FILE_TYPES = [".gif",".jpg",".jpeg",".png",".mp4",".bmp"]

##############################
# VARIABLES
####################

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

        if isfile(current) and splitext(current)[1].lower() in FILE_TYPES:
            found.append(current)

        elif isfile(current) and splitext(current)[1].lower() not in FILE_TYPES:
            logging.warning("Unrecognized file type: {}".format(splitext(current)[1].lower()))

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

########################################
if __name__ == "__main__":
    logging.info("Starting Photo Description")
    import argparse

    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join(["Find and Hash images, revealing duplicates"]))
    parser.add_argument('-t', '--target', action='append')
    parser.add_argument('-o', '--output')
    args = parser.parse_args()
    args.target = [expanduser(x) for x in args.target]
    logging.info("Finding images")
    images = find_images(args.target)
    logging.info("Hashing {} images".format(len(images)))
    hash_dict, conflicts = hash_all(images)
    logging.info("Hashed all images, {} conflicts".format(len(conflicts)))

    #write conflicts to an org file:
    with open(expanduser(args.output),'w') as f:
        f.write("* Conflicts\n")
        for x in conflicts:
            f.write("** {}\n".format(x))
            f.write("\n".join(["   [[{}]]".format(y) for y in hash_dict[x]]))
