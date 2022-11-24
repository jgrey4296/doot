#!/usr/bin/env python
##-- imports

from os import system
import argparse
import pathlib as pl
import logging as root_logger
import re
from os.path import abspath, expanduser, split, splitext, exists
from time import sleep

import requests

##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparser
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Index all tags found in orgs"]))
parser.add_argument('--target')
parser.add_argument('--separator', default=" |%| ")
parser.add_argument('--count', type=int, default=10)
parser.add_argument('--wait', type=float, default=2)
parser.add_argument('--agent')
parser.add_argument('--output')

##-- end argparser

if __name__ == '__main__':
    logging.info("---------- STARTING: Url Expander")
    args = parser.parse_args()
    args.target = pl.Path(args.target).expanduser().resolve()
    args.output = pl.Path(args.output).expanduser().resolve()

    header = {'user-agent': args.agent} if args.agent else {}



    unexpanded = []
    expanded   = {}

    ##-- load target
    logging.info("Loading %s", args.target)
    with open(args.target, 'r') as f:
        unexpanded = [x.strip() for x in f.readlines()]

    ##-- end load target

    ##-- load already expanded
    logging.info("Loading %s", args.output)
    temp_lines = []
    if exists(args.output):
        with open(args.output, 'r') as f:
            temp_lines = f.readlines()

    for line in temp_lines:
        parts = line.split(args.separator)
        expanded[parts[0].strip()] = parts[1].strip()

    ##-- end load already expanded

    logging.info("Found %s : %s", len(unexpanded), len(expanded))
    count = 0
    while count < args.count and bool(unexpanded):
        current = unexpanded.pop(0)
        if current in expanded:
            continue

        logging.debug("Handling %s/%s", count, args.count)
        try:
            response = requests.head(current, allow_redirects=True, timeout=2, headers=header)
            if response.ok:
                expanded[current] = response.url
            else:
                expanded[current] = response.status_code
        except Exception as err:
            cmd    = 'say -v Moira -r 50 "Error"'
            system(cmd)
            expanded[current] = f"400.1 : {str(err)}"
            logging.info("Error: %s", str(err))


        logging.debug("Response for %s : %s", current, expanded[current])
        with open(args.output, 'a') as f:
            f.write("{}{}{}\n".format(current, args.separator, expanded[current]))

        count += 1
        sleep(args.wait)

    logging.info("Finished")
    cmd    = 'say -v Moira -r 50 "Finished"'
    system(cmd)
