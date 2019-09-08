"""
Grouper script to put a mass of files in subdirectories
"""

from os.path import join, isfile, exists, isdir, splitext, expanduser, split
from os import listdir
from math import floor
from subprocess import call
import IPython
import argparse
# Setup root_logger:
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.grouper"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Take a subdirectory of files, group into subdirectories of size g"]))
parser.add_argument('-t', '--target', default="~/mega/savedThreads")
# parser.add_argument('-t', '--target', default="~/github/bookmark_organiser/output")
parser.add_argument('-g', '--groupnum',  default=5)
parser.add_argument('-p', '--preface', default="grouped")
args = parser.parse_args()


all_files = listdir(expanduser(args.target))
only_orgs = [x for x in all_files if splitext(x)[1] == '.org']

#group orgs into len/ratio groups
groups = [[] for x in range(args.groupnum)]
num_per_group =  floor(len(only_orgs) / args.groupnum)

count = 0
current_group = 0
for i,x in enumerate(only_orgs):
    groups[current_group].append(x)
    count += 1
    if current_group < args.groupnum-1 and count >= num_per_group:
        count = 0
        current_group += 1

#create group names
group_names = ["{}_{}".format(args.preface, x) for x in range(args.groupnum)]

logging.info("Group Names: {}".format(", ".join(group_names)))

#check no group name already exists
assert(all([not exists(join(expanduser(args.target), x)) for x in group_names]))


#create the groups
[call(['mkdir', join(expanduser(args.target), x)]) for x in group_names]
logging.info("Expanded location: {}".format(expanduser(args.target)))

#move the org files and their associated files into the
#appropriate group
for gname, group in zip(group_names, groups):
    for ofile in group:
        call(['mv',
              join(expanduser(args.target), ofile),
              join(expanduser(args.target), gname)])
        logging.info("Moving: {}".format(ofile))
        file_dir = "{}_files".format(splitext(split(ofile)[1])[0])
        logging.info("Moving: {}".format(file_dir))
        call(['mv',
              join(expanduser(args.target), file_dir),
              join(expanduser(args.target), gname)])


