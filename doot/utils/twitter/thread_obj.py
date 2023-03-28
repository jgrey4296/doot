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

@dataclass
class TwitterThreadObj:
    """ Utility Class to hold a thread
    doesn't hold the tweets themselves, just ID's
    """
    main      : list[str]       = field(default_factory=list)
    rest      : list[list[str]] = field(default_factory=list)
    quotes    : list[str]       = field(default_factory=list)
    component : pl.Path         = field(default=None)
    base_user : str             = field(default=None)

    @staticmethod
    def build(data):
        assert(all([x in data for x in ["main_thread",
                                        "rest",
                                        "quotes"]]))

        return TwitterThreadObj(data["main_thread"],
                                data["rest"],
                                data["quotes"])

    def dump(self):
        return {
            'main_thread' : self.main,
            'rest'        : self.rest,
            'quotes'      : self.quotes,
            'component'   : self.component,
            'base_user'   : self.base_user,
            }
