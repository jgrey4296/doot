#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import pathlib as pl
import datetime
import json
import logging as logmod
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from uuid import uuid1

import networkx as nx
##-- end imports

class OrgBuilderBase:

    link_pattern        : str = "[[{}]]"
    named_link_pattern  : str = "[[{}][{}]]"
    named_file_pattern  : str = "[[file:{}][{}]]"

@dataclass
class OrgStrBuilder(OrgBuilderBase):
    """
    Utility class for building Org files
    """
    output : List[Union[str, 'OrgBuilderBase']] = field(default_factory=list)

    prop_align_len      : int = 10
    heading_char        : str = "*"

    def heading(self, level, *text):
        stars = level * self.heading_char
        self.add(" ".join([stars, *text]))

    def link(self, text, uri):
        self.add(self.named_link_pattern.format(text, uri))
        self.nl

    def links(self, links):
        converted = [self.link_pattern.format(x) for x in links]
        self.add(*converted)

    def add(self, *text):
        self.output += text

    def drawer(self, name):
        drawer = OrgDrawerBuilder(self, name)
        self.add(drawer)
        return drawer

    @property
    def nl(self):
        self.output.append("")

    def __str__(self):
        return "\n".join(map(str, self.output))

@dataclass
class OrgDrawerBuilder(OrgBuilderBase):
    """
    A lazily build org drawer container,
    which aligns values in the block
    """

    owner               : OrgStrBuilder = field(default=None)
    name                : str           = field(default="")

    _contents     : List[Tuple[str, str]] = field(default_factory=list)
    _prop_pattern : str                   = ":{}:"
    _end          : str                   = ":END:"
    _max_key      : int                   = 0

    def add(self, *args):
        for name, contents in zip(args[::2], args[1::2]):
            self._contents.append((name, contents))
            self._max_key = max(len(name), self._max_key)

    def add_keyless(self, *args):
        for arg in args:
            self._contents.append(("", arg))

    def add_file_links(self, *args):
        as_links = [OrgDrawerBuilder.named_file_pattern.format(x, pl.Path(x).name) for x in args]
        self.add_keyless(*as_links)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return None

    def __str__(self):
        """
        Write the drawer, while padding appropriately
        """
        output = []
        output.append(f":{self.name.upper()}:")
        for key, val in self._contents:
            if bool(key):
                key_f   = self._prop_pattern.format(key)
                pad_amt = 5 + max(0, (2 + self._max_key) - len(key_f))
                output.append(f"{key_f}{pad_amt*' '}{val}")
            else:
                output.append(val)

        output.append(self._end)
        output.append("")
        return "\n".join(map(str, output))
