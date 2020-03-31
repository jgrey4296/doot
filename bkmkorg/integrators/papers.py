#------------------------------
# Simple program to integrate papers into a collection
#------------------------------
from hashlib import sha256
from os import listdir, mkdir
from os.path import join, isfile, exists, isdir, splitext, expanduser, split
from shutil import copyfile
import argparse
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.md5PaperChecker"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog= "\n".join(["Copies pdfs found in source dirs",
                                                    "that are not in the library dir",
                                                    "into an output dir"]))
parser.add_argument('-l', '--library', action='append')
parser.add_argument('-o', '--output', default="/Users/jgrey/Desktop/sanity_check")
parser.add_argument('-q', '--quit', action='store_true')
parser.add_argument('-s', '--source', action='append')

args = parser.parse_args()

logging.info(" LIBRARY: {}".format(args.library))
logging.info(" SOURCE: {}".format(args.source))
logging.info(" OUTPUT: {}".format(args.output))

if args.quit:
    exit()

if not isdir(args.output):
    logging.info("Making Output Dir: {}".format(args.output))
    mkdir(expanduser(args.output))

def getAllPdfs(locs, deep=0):
    """ Get the full paths of all pdfs in the location """
    assert(isinstance(deep, int))
    e_locs = [expanduser(x) for x in locs]
    assert([exists(x) for x in e_locs])
    assert(all([isdir(x) for x in e_locs]))
    queue = [(loc, 0) for loc in e_locs]
    found = []
    while bool(queue):
        (l,l_depth) = queue.pop()
        entries = listdir(l)
        pdfs = [join(l,x) for x in entries if splitext(x)[1] == ".pdf"]
        next_depth = l_depth + 1
        dirs = [(join(l,x),next_depth) for x in entries if isdir(join(l,x))]
        if bool(dirs) and l_depth < deep:
            queue += dirs
        found += pdfs
    return found

def fileToHash(filename):
    try:
        assert(isfile(filename))
    except:
        breakpoint()
    with open(filename, 'rb') as f:
        return sha256(f.read()).hexdigest()


#Get all Added file hashes
logging.info("Starting")
library_pdfs = getAllPdfs(args.library,9)
logging.info("Num of Library pdfs: {}".format(len(library_pdfs)))
library_hashmap = { fileToHash(x) : x for x in library_pdfs }
library_set = set(library_hashmap.keys())

inbox_pdfs = getAllPdfs(args.source,5)

logging.info("Num of Inbox pdfs: {}".format(len(inbox_pdfs)))
inbox_hashmap = { fileToHash(x) : x for x in inbox_pdfs }
if len(inbox_hashmap) != len(inbox_pdfs):
    inbox_hashmap = {}
    for x in inbox_pdfs:
        file_hash = fileToHash(x)
        if file_hash in inbox_hashmap:
            logging.warning("\n----- Conflict:\n{}\n{}\n{}".format(file_hash, x, inbox_hashmap[file_hash]))
        else:
            inbox_hashmap[file_hash] = x
inbox_set = set(inbox_hashmap.keys())

new_pdfs = inbox_set.difference(library_set)
logging.info("New pdfs found: {}".format(len(new_pdfs)))
for x in new_pdfs:
    name = inbox_hashmap[x]
    copyfile(name, join(args.output, split(name)[1]))


