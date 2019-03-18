"""
Copies Usable but non-parsed saved html to a separate directory
"""
from os.path import join, isfile, exists, isdir, splitext, expanduser
from os import listdir, mkdir
import argparse
from subprocess import call
# Setup root_logger:
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.error_copier"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

parser = argparse.ArgumentParser("")
parser.add_argument('-t', '--target', default="checked_errors.txt")
parser.add_argument('-s', '--source', default="~/Mega/savedTwitter")
parser.add_argument('-o', '--output', default="backup")

args = parser.parse_args()

if not exists(expanduser(args.target)):
    raise Exception("Target File does not exist")

if not exists(expanduser(args.source)):
    raise Exception("Source Directory does not exist")

if not exists(expanduser(args.output)):
    mkdir(expanduser(args.output))

to_copy = []

read_data = []
with open(expanduser(args.target)) as f:
    read_data = f.read().strip().split("\n")

for line in read_data:
    should_use, filename = [x.strip() for x in line.split('|||')]
    if should_use == 'u' and exists(expanduser(join(args.source,
                                                    filename))):
        logging.info("To Copy: {}".format(filename))
        to_copy.append(filename)
    else:
        logging.info("Discarding: {}".format(filename))

logging.info("Total to copy: {}".format(len(to_copy)))

for filename in to_copy:
    call(['cp',
          expanduser(join(args.source, filename)),
          expanduser(args.output)])
    dir_name = splitext(filename)[0]
    call(['cp', '-r',
          expanduser(join(args.source, '{}_files'.format(dir_name))),
          expanduser(args.output)])

