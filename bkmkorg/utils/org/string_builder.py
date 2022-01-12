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

file = Any

@dataclass
class OrgStrBuilder:
    """
    Utility class for building Org files
    """
    output : List[str]

    prop_align_len      : int = 10
    link_pattern        : str = "[[{}]]"
    named_link_pattern  : str = "[[{}][{}]]"
    drawer_prop_pattern : str = ":{}:"
    drawer_prop_end     : str = ":END:"
    heading_char        : str = "*"

    def heading(self, level, *text):
        stars = level * self.heading_char
        self.add(" ".join([stars, *text]))

    def link(self, text, uri):
        self.add(self.named_link_pattern.format(text, uri))

    def links(self, links):
        converted = [self.link_pattern.format(x) for x in links]
        self.add(*converted)

    def add(self, *text):
        self.output += text

    @property
    def nl(self):
        self.output.append("")

    def drawer(self, name):
        self.add(self.drawer_prop_pattern.format(name.upper()))

    def drawer_prop(self, x, y):
        prop = self.drawer_prop_pattern.format(x.upper())
        spaces = " " * max(2, (self.prop_align_len - len(prop)))
        self.add(f"{prop}{spaces}{y}")

    def drawer_end(self):
        # TODO store props, then align here
        self.add(self.drawer_prop_end)
        self.nl

    def __str__(self):
        return "\n".join(self.output)
