#!/usr/bin/env pythmn
"""
Automate twitter archiving

"""
##-- imports
from __future__ import annotations

import argparse
import configparser
import datetime
import json
import logging as root_logger
import pathlib as pl
from importlib.resources import files
from os import system
from shutil import rmtree
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import bkmkorg.io.twitter.file_writing as FFU
import bkmkorg.utils.dfs.twitter as DFSU
import bkmkorg.utils.download.twitter as DU
import bkmkorg.utils.twitter.extraction as EU
import requests
from bkmkorg import (DEFAULT_CONFIG, DEFAULT_LIBRARY, DEFAULT_SECRETS,
                     DEFAULT_TARGET)
from bkmkorg.utils.twitter.api_setup import setup_twitter
from bkmkorg.utils.twitter.graph import TwitterGraph
from bkmkorg.utils.twitter.todo_list import TweetTodoFile

import twitter

##-- end imports


##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- data
data_secrets  = files(f"bkmkorg.{DEFAULT_CONFIG}") / DEFAULT_SECRETS
data_target   = files(f"bkmkorg.{DEFAULT_CONFIG}") / DEFAULT_TARGET
##-- end data

##-- argparser
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="\n".join([""]))
parser.add_argument('--config', default=data_secrets, help="The Secrets file to access twitter")
parser.add_argument('--target', default=data_target, help="The target dir to process/download to")
parser.add_argument('--library',default=[DEFAULT_LIBRARY], action="append", help="Location of already downloaded tweets")
parser.add_argument('--export',  help="File to export all library tweet ids to, optional")
parser.add_argument('--tweet',   help="A Specific Tweet URL to handle, for CLI usage/ emacs use")
parser.add_argument('--skiptweets', action='store_true', help="for when tweets have been downloaded, or hung")
##-- end argparser

def setup_target_dict(target_dir:pl.Path, export:None|pl.Path):
    targets = {}
    targets['target_dir']           = target_dir
    targets['target_file']          = target_dir / "current.tweets"
    targets['org_dir']              = target_dir / "orgs"
    targets['tweet_dir']            = target_dir / "tweets"
    targets['combined_threads_dir'] = target_dir / "threads"
    targets['component_dir']        = target_dir / "components"
    targets['library_ids']          = target_dir / "all_ids"
    targets['users_file']           = target_dir / "users.json"
    targets['last_tweet_file']      = target_dir / "last_tweet"
    targets['download_record']      = target_dir / "downloaded.record"
    targets['lib_tweet_record']     = export or (target_dir / "lib_tweets.record")
    targets['excludes_file']        = target_dir / "excludes"

    return targets

def get_library_tweets(lib:List[pl.Path], tweet) -> Set[str]:
    library_tweet_ids = set()
    if tweet is None:
        logging.info("---------- Getting Library Tweet Details")
        logging.info("Libraries to search: %s", lib)
        library_tweet_ids = EU.get_all_tweet_ids(*lib, ext=".org")
        logging.info("Found %s library tweets", len(library_tweet_ids))

    return library_tweet_ids



def read_target_ids(tweet, target_file:pl.Path) -> TweetTodoFile:
    logging.info("---------- Getting Target Tweet ids")
    if tweet is None:
        todo_ids = TweetTodoFile.read(target_file)
    else:
        todo_ids = TweetTodoFile(mapping={tweet.name : ""})
        logging.info("Specific Tweet: %s", todo_ids)

    logging.info("Found %s source ids", len(todo_ids))
    return todo_ids

def setup(args):
    targets = setup_target_dict(args.target, args.export)

    if targets['library_ids'].exists():
        args.library.append(targets['library_ids'])

    last_tweet = False
    if targets['last_tweet_file'].exists() and args.tweet:
        with open(targets['last_tweet_file'], 'r') as f:
            last_tweet = f.read().strip()

    if args.tweet is not  None and args.tweet != last_tweet and args.target == data_target and data_target.exists():
        rmtree(str(data_target))

    missing_dirs = [x for x in [targets['target_dir'],
                                targets['tweet_dir'],
                                targets['org_dir'],
                                targets['combined_threads_dir'],
                                targets['component_dir']] if not x.exists()]

    for x in missing_dirs:
        logging.info("Creating %s Directory", x)
        x.mkdir()

    if args.tweet is not None:
        with open(targets['last_tweet_file'], 'w') as f:
            f.write(args.tweet)

    logging.info("Target Dir: %s", targets['target_dir'])
    logging.info("Library:    %s", args.library)
    logging.info("Config:     %s", args.config)

    return targets



def run_processor(targets, all_users, todo_ids, twit):
    if not bool([x for x in targets['component_dir'].iterdir() if x.suffix == ".json"]):
        logging.info("---------- Creating Components")
        FFU.construct_component_files(targets['tweet_dir'],
                                      targets['component_dir'],
                                      twit=twit)

    if not bool([x for x in targets['combined_threads_dir'].iterdir() if x.suffix == ".json"]):
        logging.info("---------- Creating user summaries")
        FFU.construct_user_summaries(targets['component_dir'], targets['combined_threads_dir'], all_users)

    logging.info("---------- Constructing org files")
    FFU.construct_org_files(targets['combined_threads_dir'], targets['org_dir'], all_users, todo_ids)

def main():
    logging.info("---------- Setup")
    args             = parser.parse_args()
    args.config      = pl.Path(args.config).expanduser().resolve()
    args.target      = pl.Path(args.target).expanduser().resolve()
    if args.library is not None:
        args.library = [pl.Path(x).expanduser().resolve() for x in args.library]
    else:
        args.library = []

    if args.export is not None:
        args.export      = pl.Path(args.export).expanduser().resolve()

    targets          = setup(args)

    config = configparser.ConfigParser(allow_no_value=True, delimiters='=')
    with open(args.config, 'r') as f:
        config.read_file(f)

    twit = setup_twitter(config)

    logging.info("---------- Setup Complete")
    logging.info("-------------------- Extracting Library Details")
    # Extract all tweet id's from library
    library_tweet_ids : Set[str] = get_library_tweets(args.library, args.tweet)

    if targets['lib_tweet_record'] is not None:
        logging.info("---------- Exporting lib tweets to: %s", targets['lib_tweet_record'])
        now : str = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(targets['lib_tweet_record'], 'a') as f:
            f.write(f"{now}:\n\t")
            f.write("\n\t".join(sorted(library_tweet_ids)))
            f.write("\n----------------------------------------\n")



    # read file of tweet id's to handle
    todo_ids : TweetTodoFile = read_target_ids(args.tweet, targets['target_file'])

    logging.info("-------------------- Downloading Todo Tweets")
    # Download tweets
    if not args.skiptweets:
        DU.download_tweets(twit, targets['tweet_dir'], todo_ids.ids(), lib_ids=library_tweet_ids)
    else:
        logging.info("Skipping tweet download")

    logging.info("-------------------- Extracting Details from Tweets")
    # Extract details from the tweets
    user_set, media_set, variant_list = EU.get_user_and_media_sets(targets['tweet_dir'])

    # write out video variant/duplicates
    with open(targets['target_dir'] / "video_variants.json", "w") as f:
        json.dump(variant_list, f, indent=4)

    logging.info("-------------------- Getting User Identities")
    # Get user identities
    all_users : Dict[str, Any] = DU.get_user_identities(targets['users_file'], twit, user_set)

    # --------------------
    logging.info("-------------------- Starting Assembly")
    # Now create threads
    run_processor(targets, all_users, todo_ids, twit)


    logging.info("-------------------- Finished Assembly")
    new_tweet_ids = get_library_tweets([targets['org_dir']],
                                       args.tweet)

    if targets['download_record'] is not None:
        logging.info("---------- Exporting lib tweets to: %s", targets['download_record'])
        now : str = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(targets['download_record'], 'a') as f:
            f.write(f"{now}:\n\t")
            f.write("\n\t".join(sorted(new_tweet_ids)))
            f.write("\n----------------------------------------\n")


    system('say -v Moira -r 50 "Finished Twitter Download"')
    logging.info("----- Finished Twitter Automation")
#  ############################################################################
if __name__ == "__main__":
    logging.info("Automated Twitter Archiver")
    main()
