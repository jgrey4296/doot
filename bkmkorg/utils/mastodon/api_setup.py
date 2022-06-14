##!/usr/bin/env python3
# pylint: disable=no-member
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import mastodon

logging = root_logger.getLogger(__name__)

Path = str

def setup_mastodon(config):
    logging.info("---------- Initialising Mastodon")
    instance = mastodon.Mastodon(
        access_token = config['MASTODON']['access_token'],
        api_base_url = config['MASTODON']['url']
    )
    return instance
