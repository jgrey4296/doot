#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import datetime
import json
import logging as logmod
import pathlib as pl
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from uuid import uuid1

import networkx as nx

##-- end imports

logging = logmod.getLogger(__name__)

__all__ = [
        "LazyComponentWriter"
]

@dataclass
class LazyComponentWriter:
    """
    An Accessor for appending data to files easily.
    comp_dir is the directory to write to
    components is the sets of tweet id's forming components

    component files are json dicts: {"tweets: [], "users": [] }

    """
    comp_dir      : pl.Path                         = field()
    components    : List[Set[str]]                  = field()

    tweet_mapping : Dict[str, set[ComponentWriter]] = field(default_factory=lambda: defaultdict(lambda: set()))
    user_mapping  : Dict[str, set[ComponentWriter]] = field(default_factory=lambda: defaultdict(lambda: set()))
    writers       : List[ComponentWriter]           = field(default_factory=list)
    missing       : Set[str]                        = field(default_factory=set)

    def __post_init__(self):
        # For each component
        for comp_set in self.components:
            # Create a writer
            comp_obj = ComponentWriter(self.comp_dir)
            assert(not comp_obj.path.exists())
            # And pair each tweet id with that writer
            self.writers.append(comp_obj)
            for x in comp_set:
                self.tweet_mapping[x].add(comp_obj)

    def __contains__(self, value):
        return value in self.tweet_mapping

    def finish(self):
        for comp_f in self.writers:
            comp_f.finish()

        self._write_summary()

    def _write_summary(self):
        summary_path = self.comp_dir / "components.summary"
        lines = [x.summary() for x in self.writers]
        summary_path.write_text("\n".join(lines))

    def add_tweets(self, data:list):
        for tweet in data:
            id_s    = tweet.get('id_str', None)
            user_id = tweet.get('user', {}).get('id_str', None)
            if id_s is None:
                continue
            if id_s not in self.tweet_mapping:
                self.missing.add(id_s)
                continue

            for comp_f in self.tweet_mapping[id_s]:
                comp_f.add(tweet)
                # Each tweet maps its user to the writer as well, for the user pass
                self.user_mapping[user_id].add(comp_f)


    def add_users(self, data:dict):
        for user_id, user in data.items():
            if user_id not in self.user_mapping:
                self.missing.add(user_id)
                continue

            for comp_f in self.user_mapping[user_id]:
                comp_f.add(user, data_type="users")

    def __enter__(self):
        return self

    def __exit__(self, atype, value, traceback):
        self.finish()

@dataclass
class ComponentWriter:
    """
    Simple interface to buffer writing tweets to a json file
    """
    dir_s        : pl.Path   = field()
    name_stem    : str       = field(default="component_{}")
    id_s         : str       = field(default_factory=lambda: str(uuid1()))
    suffix       : str       = field(default=".json")

    stored       : list[Any] = field(default_factory=list)
    tweet_ids    : set[str]  = field(default_factory=set)
    user_ids     : set[str]  = field(default_factory=set)
    write_count  : int       = field(default=20)
    state        : str       = field(default="pre")

    write_states : ClassVar[list[str]] = ["pre", "writing_tweets", "mid", "writing_users", "finished"]

    def __hash__(self):
        return id(self)

    @property
    def path(self):
        return (self.dir_s / self.name_stem.format(self.id_s)).with_suffix(self.suffix)

    def finish(self):
        """ Add the final ] to the file """
        self._maybe_dump(force=True)
        with open(self.path, 'a') as f:
            f.write("\n    ]\n}")
        self.state = "finished"


    def add(self, data, data_type="tweets"):
        """ Add a tweet lazily into the component file """
        match self.state, data_type:
            case "pre" | "writing_tweets", "tweets":
                self.stored.append(data)
                self.tweet_ids.add(data['id_str'])
                self._maybe_dump()
            case "pre" | "writing_tweets", "users":
                logging.debug("Switching Writer to users")
                self._maybe_dump(force=True)
                self.state = "mid"
                self.user_ids.add(data['id_str'])
                self.stored.append(data)
                self._maybe_dump()
            case "mid" | "writing_users", "users":
                self.stored.append(data)
                self.user_ids.add(data['id_str'])
                self._maybe_dump()
            case _:
                raise TypeError("Unexpected State for writer", self.state, data_type)


    def _maybe_dump(self, force=False):
        """
        Dump queued tweets into the component file
        """
        assert(not self.state == "finished")
        if (not force) and len(self.stored) < self.write_count:
            return
        if not bool(self.stored):
            return

        # convert to str, chop of brackets
        write_str = json.dumps(self.stored, indent=4)[2:-2]
        with open(self.path, 'a') as f:
            match self.state:
                case "pre":
                    f.write("{\n    \"tweets\": [\n")
                    self.state = "writing_tweets"
                case "writing_tweets" | "writing_users":
                    f.write(",\n")
                case "mid":
                    f.write("\n    ],\n    \"users\": [\n")
                    self.state = "writing_users"

            f.write(write_str)

        self.stored.clear()



    def summary(self):
        tweet_ids = " ".join(self.tweet_ids)
        user_ids  = " ".join(self.user_ids)
        comp_name = self.path.stem
        return f"Component: {comp_name} Counts: [{len(self.tweet_ids)} {len(self.user_ids)}] TweetIds: [{tweet_ids}] UserIds: [{user_ids}]"
