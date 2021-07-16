#!/opt/anaconda3/envs/bookmark/bin/python
"""
Automate twitter archiving

"""
import argparse
import configparser
import datetime
import json
import logging as root_logger
import re
import sys
import uuid
from os import listdir, mkdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from shutil import copyfile, rmtree
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import bkmkorg.io.twitter.dfs_utils as DFSU
import bkmkorg.io.twitter.download_utils as DU
import bkmkorg.io.twitter.extract_utils as EU
import bkmkorg.io.twitter.file_format_utils as FFU
import networkx as nx
import requests

import twitter

DEFAULT_CONFIG = "secrets.config"
DEFAULT_TARGET = ".temp_download"


# Setup root_logger:
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="\n".join([""]))
parser.add_argument('--config', default=DEFAULT_CONFIG, help="The Secrets file to access twitter")
parser.add_argument('--target', default=DEFAULT_TARGET, help="The target dir to process/download to")
parser.add_argument('--library', action="append",       help="Location of already downloaded tweets")
parser.add_argument('--export',  help="File to export all library tweet ids to, optional")
parser.add_argument('--tweet', help="A Specific Tweet URL to handle, for CLI usage/ emacs use")
parser.add_argument('--skiptweets', action='store_true', help="for when tweets have been downloaded, or hung")




def get_library_tweets(lib, tweet, export):
    library_tweet_ids = set()
    if tweet is None:
        logging.info("---------- Getting Library Tweet Details")
        library_tweet_ids = EU.get_all_tweet_ids(*lib)
        logging.info("Found {} library tweets".format(len(library_tweet_ids)))

    if tweet is None and export is not None:
        logging.info("---------- Exporting to: {}".format(export))
        with open(export, 'w') as f:
            f.write("\n".join(library_tweet_ids))
            sys.exit()

    return library_tweet_ids



def read_target_ids(tweet, target_file):
    logging.info("---------- Getting Target Tweet ids")
    if tweet is None:
        source_ids = set(EU.extract_tweet_ids_from_file(target_file,
                                                        simple=True))
    else:
        source_ids = set([split(tweet)[1]])
        logging.info("Specific Tweet: {}".format(source_ids))

    logging.info("Found {} source ids".format(len(source_ids)))

    return source_ids

def main():

    ####################
    # Setup argparser
    args = parser.parse_args()
    args.config = abspath(expanduser(args.config))
    if args.library is not None:
        args.library = [abspath(expanduser(x)) for x in args.library]
    else:
        args.library = []

    if args.export is not None:
        args.export = abspath(expanduser(args.export))

    # Auto setup
    target_dir           = abspath(expanduser(args.target))
    target_file          = join(target_dir, "bookmarks.txt")
    org_dir              = join(target_dir, "orgs")
    tweet_dir            = join(target_dir, "tweets")
    combined_threads_dir = join(target_dir, "threads")
    component_dir        = join(target_dir, "components")
    library_ids          = join(target_dir, "all_ids")
    users_file           = join(target_dir, "users.json")
    last_tweet_file      = join(target_dir, "last_tweet")

    if exists(library_ids):
        args.library.append(library_ids)

    last_tweet = False
    if exists(last_tweet_file) and args.tweet:
        with open(last_tweet_file, 'r') as f:
            last_tweet = f.read().strip()

    if args.tweet != None and args.tweet != last_tweet and args.target == DEFAULT_TARGET and exists(DEFAULT_TARGET):
        rmtree(DEFAULT_TARGET)

    missing_dirs = [x for x in [target_dir,
                                tweet_dir,
                                org_dir,
                                combined_threads_dir,
                                component_dir] if not exists(x)]

    for x in missing_dirs:
        logging.info("Creating {} Directory".format(x))
        mkdir(x)

    if args.tweet != None:
        with open(last_tweet_file, 'w') as f:
            f.write(args.tweet)

    logging.info("Target Dir: {}".format(target_dir))
    logging.info("Library: {}".format(args.library))
    logging.info("Config: {}".format(args.config))
    ####################
    # Read Configs
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

    logging.info("-------------------- Extracting Pre-Details")
    # Extract all tweet id's from library
    library_tweet_ids = get_library_tweets(args.library,
                                           args.tweet,
                                           args.export)

    # read file of tweet id's
    source_ids = read_target_ids(args.tweet, target_file)
    logging.info("-------------------- Downloading data")
    # Download tweets
    if not args.skiptweets:
        DU.download_tweets(twit, tweet_dir, source_ids, lib_ids=library_tweet_ids)
    else:
        logging.info("Skipping tweet download")

    # Extract details from the tweets
    user_set, media_set, variant_list = EU.get_user_and_media_sets(tweet_dir)

    # write out video variant/duplicates
    with open(join(target_dir, "video_variants.json"), "w") as f:
        json.dump(variant_list, f, indent=4)

    # DEPRECATED, is downloaded when org is constructed now:
    # DU.download_media(media_dir, media_set)

    # Get user identities
    all_users = DU.get_user_identities(users_file, twit, user_set)

    # --------------------
    logging.info("-------------------- Finished Retrieval")
    try:
        # Now create threads
        if not bool([x for x in listdir(component_dir) if splitext(x)[1] == ".json"]):
            logging.info("---------- Assembling Threads")
            di_graph = FFU.assemble_threads(tweet_dir)
            logging.info("---------- Creating Components")
            components = DFSU.dfs_for_components(di_graph)
            FFU.create_component_files(components, tweet_dir, component_dir, di_graph, twit=twit)

        if not bool([x for x in listdir(combined_threads_dir) if splitext(x)[1] == ".json"]):
            logging.info("---------- Creating user summaries")
            FFU.construct_user_summaries(component_dir, combined_threads_dir, all_users)

        logging.info("---------- Constructing org files")
        FFU.construct_org_files(combined_threads_dir, org_dir, all_users)
    except Exception as err:
        logging.exception("Exception occurred: {}".format(err))


if __name__ == "__main__":
   logging.info("Automated Twitter Archiver")
   main()
