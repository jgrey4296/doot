"""
    A Script to automate its way through a tree of directories,
    and call mutool on each pdf to convert it to text in an output directory
"""
##############################
# IMPORTS
####################
import logging as root_logger
import subprocess
from os.path import splitext, split
from os.path import join, isfile, exists, abspath
from os.path import isdir, expanduser
from os import listdir, mkdir
import argparse

# Setup root_logger:
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

#Arg Parser
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))
parser.add_argument('-l', '--library')
parser.add_argument('-o', '--output')

##############################
# CONSTANTS
####################

##############################
# VARIABLES
####################

##############################
# Utilities
####################
def convert(source, output_dir, title):
    target = "{}.txt".format(title)
    logging.info("Converting {} from {}".format(target, source))
    subprocess.run(['mutool',
                    'convert',
                    '-F', 'text',
                    '-o', join(output_dir, target),
                    source],
                   stdout=subprocess.PIPE)


##############################
# Core Functions
####################

########################################
if __name__ == "__main__":
    logging.info("Starting ")
    args = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    args.output = abspath(expanduser(args.output))

    if not isdir(args.output):
        mkdir(args.output)

    stack = [join(args.library, x) for x in listdir(args.library)]
    while bool(stack):
        current = stack.pop(0)
        if isdir(current):
            logging.info("Listing: {}".format(current))
            stack += [join(current, x) for x in listdir(current)]
        else:
            path, fname = split(current)
            title, ext = splitext(fname)
            if ext == ".pdf":
                convert(current, args.output, title)
