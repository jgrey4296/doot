#!/usr/bin/env python3
import datetime
import json
import logging as root_logger
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from os import listdir, mkdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from uuid import uuid1

import networkx as nx
from bkmkorg.utils.download.media import download_media
from bkmkorg.utils.download.twitter import download_tweets
from bkmkorg.utils.org.string_builder import OrgStrBuilder

logging = root_logger.getLogger(__name__)


@dataclass
class TweetComponents:
    """
    An Accessor for appending data to files easily.
    comp_dir is the directory to write to
    components is the sets of tweet id's forming components
    """
    comp_dir   : str
    components : List[Set[str]]

    mapping    : Dict[str, List['ComponentWriter']] = field(default_factory=lambda: defaultdict(lambda: []))
    writers    : List['ComponentWriter']            = field(default_factory=list)
    missing    : Set[str]                           = field(default_factory=set)
    # TODO record missing

    @dataclass
    class ComponentWriter:
        """
        Simple interface to buffer writing tweets to a json file
        """
        dir_s        : str
        name_pattern : str  = field(default="component_{}.json")
        started      : bool = field(default=False)
        finished     : bool = field(default=False)
        id_s         : str  = field(default_factory=lambda: str(uuid1()))

        stored       : List[Any] = field(default_factory=list)
        write_count  : int  = field(default=20)

        @property
        def path(self):
            return join(self.dir_s, self.name_pattern.format(self.id_s))

        def finish(self):
            """ Add the final ] to the file """
            self._maybe_dump(force=True)
            with open(self.path, 'a') as f:
                f.write("\n]")
            self.finished = True

        def add(self, data):
            """ Add a tweet lazily into the component file """
            self.stored.append(data)
            self._maybe_dump()

        def _maybe_dump(self, force=False):
            """
            Dump queued tweets into the component file
            """
            if (not force) and len(self.stored) < self.write_count:
                return
            if not bool(self.stored):
                return

            assert(not self.finished)
            # convert to str, chop of brackets
            write_str = json.dumps(self.stored, indent=4)[2:-2]
            with open(self.path, 'a') as f:
                if not self.started:
                    f.write("[\n")
                    self.started = True
                else:
                    f.write(",\n")

                f.write(write_str)

            self.stored.clear()

    # End of ComponentWriter
    def __post_init__(self):
        # For each component
        for comp_set in self.components:
            # Create a writer
            comp_obj = TweetComponents.ComponentWriter(self.comp_dir)
            assert(not exists(comp_obj.path))
            # And pair each tweet id with that writer
            self.writers.append(comp_obj)
            for x in comp_set:
                self.mapping[x].append(comp_obj)

    def __contains__(self, value):
        return value in self.mapping

    def finish(self):
        for comp_f in self.writers:
            comp_f.finish()

    def add(self, data:Dict[Any,Any], *ids:str):
        assert(all([isinstance(x, str) for x in ids]))
        for id_s in ids:
            if id_s not in self.mapping:
                self.missing.add(id_s)
                continue

            for comp_f in self.mapping[id_s]:
                comp_f.add(data)

    def __enter__(self):
        return self

    def __exit__(self, atype, value, traceback):
        self.finish()
