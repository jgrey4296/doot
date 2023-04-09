#!/usr/bin/env python
"""
Tagset Reading

"""
##-- imports
from __future__ import annotations

import logging as logmod
import re
from dataclasses import dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast, Final, TypeAlias)

import networkx as nx
import regex
from doot.utils.formats.bookmarks import BookmarkCollection
from doot.utils.formats.tagfile import TagFile
##-- end imports

logging = logmod.getLogger(__name__)

IGNORE_REPLACEMENTS = ["TO_CHECK"]

TAG_NORM    : Final[re.Pattern] = regex.compile(" +")
ORG_PATTERN : Final[str]        = r"^\*\*\s+.+?\s+:(\S+):$"
ORG_SEP     : Final[str]        = ":"

Tag : TypeAlias = str

class TagGraph:

    def __init__(self):
        self.graph : nx.Graph = nx.Graph()

    def extract_bibtex(self, db:bibtexparser.BibtexDatabase) -> TagFile:
        logging.info("Processing Bibtex: %s", len(db.entries))

        proportion = int(len(db.entries) / 10)
        count = 0
        total = TagFile()

        for i, entry in enumerate(db.entries):
            if i % proportion == 0:
                logging.info("%s/10 Complete", count)
                count += 1

            #get tags
            total.update(self.link(entry['tags']))

        return total

    def extract_org(self, org_files:List[pl.Path], tag_regex=None) -> TagFile:
        logging.info("Extracting data from orgs")
        tag_regex = tag_regex or ORG_PATTERN

        ORG_TAG_REGEX = regex.compile(tag_regex)
        total = TagFile()

        for org in org_files:
            #read
            text = []
            with open(org,'r') as f:
                text = f.readlines()

            #line by line
            for line in text:
                tags = ORG_TAG_REGEX.findall(line)
                e_tags = []
                if not bool(tags):
                    continue

                e_tags = [x for x in tags[0].split(ORG_SEP)]
                total.update(self.link(e_tags))

        return total

    def extract_bookmark(self, bkmk_files: List[pl.Path]) -> TagFile:
        total = TagFile()
        for bkmk_f in bkmk_files:
            bkmks = BookmarkCollection.read(bkmk_f)

            for bkmk in bkmks:
                tags          = bkmk.tags
                total.update(self.link(tags))

        return total

    def link(self, tags:Iterable[Tag]) -> Iterable[Tag]:
        """
        Add a set of tags to the graph, after normalising
        """
        norm_tags = [TAG_NORM.sub("_", x.strip()) for x in tags if bool(x)]
        remaining = norm_tags[:]

        [self.graph.add_node(x, count=0) for x in norm_tags if x not in self.graph]

        for tag in norm_tags:
            self.graph.nodes[tag]['count'] += 1
            remaining.remove(tag)
            edges_to_increment = [(tag, y) for y in remaining]
            for u,v in edges_to_increment:
                if not self.graph.has_edge(u,v):
                    self.graph.add_edge(u,v, weight=0)

                self.graph[u][v]['weight'] += 1

        return norm_tags

    def write(self, target:pl.Path):
        nx.write_weighted_edgelist(self.graph, str(target))

    def __str__(self):
        keys    = self.tags
        tag_str = "\n".join(["{} : {}".format(k, self.graph.nodes[k]['count']) for k in keys])
        return tag_str

    @property
    def tags(self) -> TagFile:
        result = TagFile()
        for tag in self.graph.nodes:
            result.set_count(tag, self.graph.nodes[tag]['count'])
        return result

    def get_count(self, tag:Tag):
        if tag not in self.graph:
            return 0
        return self.graph[tag]['count']
