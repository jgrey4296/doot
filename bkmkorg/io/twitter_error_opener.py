"""
An Automated opener for html files that triggered errors
"""
import IPython
from os import listdir
from os.path import join, isfile, exists, isdir, splitext, expanduser
from subprocess import call
import argparse
import logging as root_logger

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.error_opener"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Go through all errors from a twitter parse, and mark them for deletion or keeping"]))
parser.add_argument('-f', '--file')
parser.add_argument('-t', '--target', default="~/Mega/twitterthreads")
parser.add_argument('-o', '--output', default="./output/checked_errors.txt")

args = parser.parse_args()

target_file = expanduser(args.file)
error_htmls = None

with open(target_file, 'r') as f:
    error_htmls = f.read().split("\n")

with open(args.output,'a') as f:
    f.write("--------------------\n\n")

assert(error_htmls is not None)
for x in error_htmls:
    full_path = expanduser(join(args.target, x))
    assert(exists(full_path))
    logging.info("Current: {}".format(full_path))
    call(['open',full_path])
    result = input("Mark Result: ")
    logging.info("Marked: {}".format(result))
    with open(args.output, 'a') as f:
        f.write("{} ||| {}\n".format(result, x))
