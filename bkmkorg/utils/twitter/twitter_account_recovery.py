#!/usr/bin/env python3
# https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
import argparse
import configparser
import json
import logging as root_logger
import time
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import requests

import twitter

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
DEFAULT_CONFIG = "secrets.config"

def get_user_identities(users_file, twit, users):
    """ Get all user identities from twitter """
    logging.info("Getting user identities")
    total_users = {}
    user_queue  = list(users)
    if exists(users_file):
        with open(users_file,'r') as f:
            total_users.update({x['id_str'] : x for x in  json.load(f, strict=False)})

        users -= total_users.keys()
        logging.info("Already retrieved {}, {} remaining".format(len(total_users), len(users)))
        user_queue = list(users)

    try:
        while bool(user_queue):
            current = user_queue[:100]
            user_queue = user_queue[100:]

            try:
                data = twit.UsersLookup(user_id=current)
                logging.info("Retrieved: {}".format(len(data)))
                new_users = [json.loads(x.AsJsonString()) for x in data]
                total_users.update({x['id_str'] : x for x in new_users})

            except twitter.error.TwitterError as err:
                logging.info("Does not exist: {}".format(current))
            except requests.exceptions.ConnectionError as err:
                breakpoint()

            finally:
                time.sleep(30)

    finally:
        logging.info("Saving {}".format(len(total_users)))
        with open(users_file, 'w') as f:
            json.dump(list(total_users.values()), f, sort_keys=True, indent=4)

    return total_users


if __name__ == "__main__":
    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n".join([""]))
    parser.add_argument('--config', default=DEFAULT_CONFIG, help="The Secrets file to access twitter")
    parser.add_argument('--target', help="the json file with account information")
    parser.add_argument('--output', help="the output file")

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
    logging.info("Loaded Json, got {} ids".format(len(id_list)))

    get_user_identities(args.output, twit, id_list)
