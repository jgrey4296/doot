#!/usr/bin/env py
# pylint: disable=no-memberthon3
##-- imports
from __future__ import annotations

import pathlib as pl
import logging as root_logger
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import twitter as tw
##-- end imports

logging = root_logger.getLogger(__name__)

def setup_twitter(config):
    logging.info("---------- Initialising Twitter")
    should_sleep = config['DEFAULT']['SLEEP'] == "True"
    twit = tw.Api(consumer_key=config['TWITTER']['consumerKey'],
                  consumer_secret=config['TWITTER']['consumerSecret'],
                  access_token_key=config['TWITTER']['accessToken'],
                  access_token_secret=config['TWITTER']['accessSecret'],
                  sleep_on_rate_limit=should_sleep,
                  tweet_mode='extended')

    return twit


def load_credentials_and_setup(credentials:pl.Path, key:pl.Path, secret:pl.Path):
    """ Load the keys and tokens, and setup the twitter client """
    #Get the Key and Secret from (gitignored) files
    MY_TWITTER_CREDS = credentials
    KEY_FILE         = key
    SECRET_FILE      = secret

    assert(all([x.exists() for x in [MY_TWITTER_CREDS, KEY_FILE, SECRET_FILE]]))

    logging.info("Setting up Twitter Client")
    with open(KEY_FILE,"r") as f:
        C_KEY = f.read().strip()
    with open(SECRET_FILE, "r") as f:
        C_SECRET = f.read().strip()

    if not exists(MY_TWITTER_CREDS):
        tw.oauth_dance("jgNetworkAnalysis", C_KEY, C_SECRET, MY_TWITTER_CREDS)

    TOKEN, TOKEN_SECRET = tw.read_token_file(str(MY_TWITTER_CREDS))
    assert(all([x is not None for x in [C_KEY, C_SECRET, TOKEN, TOKEN_SECRET]]))
    return tw.Twitter(auth=tw.OAuth(TOKEN, TOKEN_SECRET, C_KEY, C_SECRET))
