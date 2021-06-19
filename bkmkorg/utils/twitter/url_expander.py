#!/opt/anaconda3/envs/bookmark/bin/python

import re
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

import requests
from bkmkorg.utils.file.retrieval import get_data_files

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

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Index all tags found in orgs"]))
parser.add_argument('--target')
parser.add_argument('--count', type=int, default=10)
parser.add_argument('--output')

SHORT_URL_RE = re.compile()

if __name__ == '__main__':
    args = parser.parse_args()
    args.target = abspath(expanduser(args.target))
    args.output = abspath(expanduser(args.output))

    unexpanded = []
    expanded   = {}

    # load the targets
    logging.info(f"Loading {args.target}")
    with open(args.target, 'r') as f:
        unexpanded = f.readlines()

    # load the output
    logging.info(f"Loading {args.output}")
    temp_lines = []
    with open(args.output, 'r') as f:
        temp_lines = f.readlines()

    for line in temp_lines:
        parts = line.split(":")
        expanded[parts[0].strip()] = parts[1].strip()

    logging.info(f"Found {len(unexpanded)} : {len(expanded)}")

    count = 0
    while count < args.count and bool(unexpanded):
        current = unexpanded.pop(0)
        if current in expanded:
            continue

        response = requests.head(current, allow_redirects=True)
        if response.ok:
            expanded[current] = response.url
        else:
            expanded[current] = response.status_code

        logging.info(f"Response for {current} : {expanded[current]}")
        count += 1

    to_string = "\n".join(["{} : {}".format(x,y) for x,y in expanded.items()])

    with open(args.output, 'w') as f:
        f.write(to_string)
