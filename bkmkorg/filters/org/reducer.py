#!/usr/bin/env python
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import pathlib as pl
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

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["MP4 duplicate remover"]))
parser.add_argument('--target', action="append", required=True)
parser.add_argument('--tweets', default="~/Desktop/twitter/tweets")
parser.add_argument('--archive')
##-- end argparse


# TODO see /Volumes/documents/github/py_bookmark_organiser/bkmkorg/io/twitter_automator.py

if __name__ == "__main__":
    args = parser.parse_args()
    #args.aBool...

    # Setup twitter

    # Get orgs
    path = str
    orgs: List[path] = []
    # load in an org
    for org in orgs:
        # get all files
        files_for_org: List[path] = []
        # get all tweets with mp4's in
        tweet_ids: List[str] = []
        # get info for tweets
        tweets: List[Any] = []

        # for each tweet:
        for tweet in tweets:
            # Lookup in tweets location
            # if not there, get from twitter

            # Get media from tweet
            # Get variants, strip junk from name,
            # Get bitrate
            ## save chosen/reject files by bitrate
            continue

        # compare chosen/reject list to found files
        # move reject list to storage
        # list files not in chosen/reject
