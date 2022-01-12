#!/usr/bin/env python3
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic
from os.path import exists, expanduser, isdir, isfile, join, splitext

import twitter as tw

Path = str


def load_credentials_and_setup(credentials:Path, key:Path, secret:Path):
    """ Load the keys and tokens, and setup the twitter client """
    #Get the Key and Secret from (gitignored) files
    MY_TWITTER_CREDS = absfile(expanduser(credentials))
    KEY_FILE         = absfile(expanduser(key))
    SECRET_FILE      = absfile(expanduser(secret))

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
