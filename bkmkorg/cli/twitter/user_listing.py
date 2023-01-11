"""
script to get all users I follow, and create a file to annotate list membership
with details including bio
"""
##-- imports
from __future__ import annotations

import pathlib as pl
import argparse
import logging as root_logger
import pickle
import textwrap
from functools import partial

from bkmkorg.twitter.api_setup import load_credentials_and_setup
from bkmkorg.twitter import listing
import twitter as tw

##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.user_listing"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparse
parser = argparse.ArgumentParser("")
# todo: add output filename target
parser.add_argument('-t', '--target', default='output.org')
parser.add_argument('-b', '--backup', default='backup_')
parser.add_argument('-c', '--credentials', default="my.credentials")
parser.add_argument('-k', '--key', default='consumer.key')
parser.add_argument('-s', '--secret', default='consumer.secret')

##-- end argparse


def main():
    args = parser.parse_args()
    args.target      = pl.Path(args.target).expanduser().resolve()
    args.backup      = pl.Path(args.backup).expanduser().resolve()
    args.credentials = pl.Path(args.credentials).expanduser().resolve()
    args.key         = pl.Path(args.key).expanduser().resolve()
    args.secret      = pl.Path(args.secret).expanduser().resolve()

    backup_ids = args.backup.with_suffix(".ids")

    t = load_credentials_and_setup(str(args.credentials),
                                   str(args.key),
                                   str(args.secret))
    friends = []
    #Get all friends if you haven't already
    if not backup_ids.exists():
        friends = listing.get_friends(t)
        with open(backup_ids, 'w') as f:
            for id_str in friends:
                f.write("{}\n".format(id_str))
    else:
        with open(backup_ids,'r') as f:
            friends = f.read().split('\n')
    listing.init_file(args.target)

    listing.get_users(t, friends, partial(listing.append_to_file, args.target), args.backup)
    logging.info("Retrieval complete")

##-- ifmain
if __name__ == '__main__':
    main()

##-- end ifmain
