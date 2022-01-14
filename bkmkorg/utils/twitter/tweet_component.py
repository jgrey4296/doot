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

logging = root_logger.getLogger(__name__)

from bkmkorg.utils.download.twitter import download_tweets
from bkmkorg.utils.download.media import download_media
from bkmkorg.utils.org.string_builder import OrgStrBuilder


@dataclass
class TweetComponent:
    """
    Create and write Twitter thread Components to json
    """
    comp_dir : str
    components : List[Set[str]]

    mapping : Dict[str, List['ComponentWriter']] = field(default_factory=lambda: defaultdict(lambda: []))
    missing : Set[str] = field(default_factory=set)
    # TODO record missing

    @dataclass
    class ComponentWriter:
        """
        Simple interface to repeatedly append tweets to a json file
        """
        dir_s        : str
        name_pattern : str  = field(default="component_{}.json")
        started      : bool = field(default=False)
        finished     : bool = field(default=False)
        id_s         : str  = field(default_factory=lambda: str(uuid1()))

        @property
        def path(self):
            return join(self.dir_s, self.name_pattern.format(self.id_s))

        def finish(self):
            """ Add the final ] to the file """
            with open(self.path, 'a') as f:
                f.write("]")
            self.finished = True

        def add(self, data):
            assert(not self.finished)
            with open(self.path, 'a') as f:
                if not self.started:
                    f.write("[")
                    self.started = True
                else:
                    f.write(",")
                f.write(json.dumps(data, indent=4))

    # End of ComponentWriter
    def __post_init__(self):
        for comp_set in self.components:
            # Then to each id in that component:
            comp_obj = TweetComponent.ComponentWriter(self.comp_dir)
            assert(not exists(comp_obj.path))
            for x in comp_set:
                self.mapping[x].append(comp_obj)

    def __contains__(self, value):
        return value in self.mapping

    def finish(self):
        for comp_f in self.mapping.values():
            comp_f.finish()


    def add(self, data, *ids):
        assert(all([isinstance(x, str) for x in ids]))
        for id_s in ids:
            if id_s not in self.mapping:
                self.missing.add(id_s)
                continue

            for comp_f in self.mapping[id_s]:
                comp_f.add(data)

    def __enter__(self):
        pass

    def __exit__(self, atype, value, traceback):
        self.finish()
