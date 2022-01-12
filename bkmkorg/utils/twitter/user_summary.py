#!/usr/bin/env python3
import json
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

from os import listdir, mkdir
from collections import defaultdict
from uuid import uuid1
import datetime
import logging as root_logger
import networkx as nx
logging = root_logger.getLogger(__name__)

@dataclass
class TwitterUserSummary:
    """
    Collects separate threads and tweets together by the originating user
    """
    id_s         : str
    dir_s        : str
    name_pattern : str               = field(default="user_{}.json")
    user         : Any               = field(default=None)
    threads      : List['ThreadObj'] = field(default_factory=list)
    tweets       : Dict[str, Any]    = field(default_factory=dict)

    _has_media   : bool              = field(default=False)

    @dataclass
    class ThreadObj:
        """ Utility Class to hold a thread """
        main   : List[str]       = field(default_factory=list)
        rest   : List[List[str]] = field(default_factory=list)
        quotes : List[str]       = field(default_factory=list)
        total  : List[str]       = field(default_factory=list)

        def __post_init__(self):
            # init total from main, rest, quotes
            totals = set(self.main)
            totals.update([y for x in self.rest for y in x])
            totals.update(self.quotes)
            self.total.update(totals)

        def dump(self):
            return {
                'main_thread' : self.main,
                'rest' : self.rest,
                'quotes' : self.quotes,
                'total' : self.total
                }

    # End of ThreadObj
    def __post_init__(self):
        self.read()

    def has_media(self, value=None):
        if isinstance(value, bool):
            self._has_media = self._has_media or value
        return self._has_media

    def set_user(self, value):
        if isinstance(value, str):
            self.user = {'screen_name': value}
        else:
            assert(isinstance(value, dict))
            self.user = value

    @property
    def path(self):
        return join(self.dir_s, self.name_pattern.format(self.id_s))

    def read(self):
        if not exists(self.path):
            return

        # Get raw
        with open(self.path, 'r') as f:
            user_data = json.load(f, strict=False)

        # add to obj
        raise NotImplementedError()


    def write(self):
        # Build data into a basic dict
        user_data = {
            'has_media' : self.has_media,
            'user'      : self.user,
            'threads'   : [x.dump() for x in self.threads],
            'tweets'    : self.tweets,
        }

        # Then write data
        with open(self.path, 'w') as f:
            json.dump(user_data, f, indent=4)

    def add_thread(self, main:List[str], rest:List[List[str]], quotes:Set[str], tweets:List[Any]):
        # Build Thread Obj
        obj = TwitterUserSummary.ThreadObj(main, rest, list(quotes))

        # Add to self
        self.threads.append(obj)
        self.tweets.update(tweets)

        # Update media status
        self.has_media(any([bool(TwitterTweet.get_tweet_media(x)) for x in tweets.values()]))
