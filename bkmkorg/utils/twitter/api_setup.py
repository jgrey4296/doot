#!/usr/bin/env python3
# pylint: disable=no-member
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import twitter as tw

logging = root_logger.getLogger(__name__)

Path = str


def load_credentials_and_setup(credentials:Path, key:Path, secret:Path):
    """ Load the keys and tokens, and setup the twitter client """
    #Get the Key and Secret from (gitignored) files
    MY_TWITTER_CREDS = abspath(expanduser(credentials))
    KEY_FILE         = abspath(expanduser(key))
    SECRET_FILE      = abspath(expanduser(secret))

    assert(all([exists(x) for x in [MY_TWITTER_CREDS, KEY_FILE, SECRET_FILE]]))

    logging.info("Setting up Twitter Client")
    with open(KEY_FILE,"r") as f:
        C_KEY = f.read().strip()
    with open(SECRET_FILE, "r") as f:
        C_SECRET = f.read().strip()

    if not exists(MY_TWITTER_CREDS):
        tw.oauth_dance("jgNetworkAnalysis", C_KEY, C_SECRET, MY_TWITTER_CREDS)

    TOKEN, TOKEN_SECRET = tw.read_token_file(MY_TWITTER_CREDS)
    assert(all([x is not None for x in [C_KEY, C_SECRET, TOKEN, TOKEN_SECRET]]))
    return tw.Twitter(auth=tw.OAuth(TOKEN, TOKEN_SECRET, C_KEY, C_SECRET))
