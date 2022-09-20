##!/usr/bin/env python3
# pylint: disable=no-member
##-- imports
from __future__ import annotations

import pathlib as pl
import logging as root_logger
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import mastodon
##-- end imports

logging = root_logger.getLogger(__name__)

def setup_mastodon(config):
    logging.info("---------- Initialising Mastodon")
    instance = mastodon.Mastodon(
        access_token = config['MASTODON']['access_token'],
        api_base_url = config['MASTODON']['url']
    )
    return instance
