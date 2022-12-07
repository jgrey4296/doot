#!/usr/bin/env python
"""


"""
##-- imports
import argparse
import configparser
import json
import logging as root_logger
import time
from importlib.resources import files
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import requests
import twitter
from bkmkorg import DEFAULT_BOTS, DEFAULT_CONFIG
from bkmkorg.twitter.user_ids import get_user_identities

##-- end imports

data_path = files(f"bkmkorg.{DEFAULT_CONFIG}")
data_bots = data_path.joinpath(DEFAULT_BOTS)

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
                                    epilog="\n".join([""]))
parser.add_argument('--config', default=data_path, help="The Secrets file to access twitter")
parser.add_argument('--target', help="the json file with account information")
parser.add_argument('--output', help="the output file")
##-- end argparser


##############################
DEFAULT_CONFIG = "secrets.config"


def main():
    args = parser.parse_args()
    args.config = abspath(expanduser(args.config))
    args.target = abspath(expanduser(args.target))
    args.output = abspath(expanduser(args.output))

    config = configparser.ConfigParser()
    with open(args.config, 'r') as f:
        config.read_file(f)
    ####################
    # INIT twitter object
    logging.info("---------- Initialising Twitter")
    twit = twitter.Api(consumer_key=config['DEFAULT']['consumerKey'],
                       consumer_secret=config['DEFAULT']['consumerSecret'],
                       access_token_key=config['DEFAULT']['accessToken'],
                       access_token_secret=config['DEFAULT']['accessSecret'],
                       sleep_on_rate_limit=config['DEFAULT']['sleep'],
                       tweet_mode='extended')

    with open(args.target, 'r') as f:
        data = json.load(f)

    assert(data is not None)

    id_list = [str(x) for x in data['ids']]
    logging.info("Loaded Json, got %s ids", len(id_list))

    get_user_identities(args.output, twit, id_list)


##-- ifmain
if __name__ == "__main__":
    main()
##-- end ifmain
