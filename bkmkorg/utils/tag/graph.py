#!/usr/bin/env python
"""
Tagset Reading

"""
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import networkx as nx
import regex
from bkmkorg.io.reader.netscape import open_and_extract_bookmarks
from bkmkorg.io.reader.plain_bookmarks import load_plain_file
from bkmkorg.utils.tag.collection import TagFile

logging = root_logger.getLogger(__name__)

IGNORE_REPLACEMENTS = ["TO_CHECK"]

TAG_NORM = regex.compile(" +")

def extract_tags_from_bibtex(db, the_graph=None) -> nx.Graph:
    logging.info("Processing Bibtex: {}".format(len(db.entries)))
    if the_graph is None:
        logging.info("Creating new graph")
        the_graph = nx.Graph()

    proportion = int(len(db.entries) / 10)
    count = 0

    for i, entry in enumerate(db.entries):
        if i % proportion == 0:
            logging.info("{}/10 Complete".format(count))
            count += 1

        #get tags
        e_tags = [TAG_NORM.sub("_", x.strip()) for x in entry['tags']]
        remaining = list(e_tags)

        [the_graph.add_node(x, count=0) for x in e_tags if x not in the_graph]
        for x in e_tags:
            the_graph.nodes[x]['count'] += 1

            remaining.remove(x)
            edges_to_increment = [(x,y) for y in remaining]
            for u,v in edges_to_increment:
                if not the_graph.has_edge(u,v):
                    the_graph.add_edge(u,v, weight=0)
                the_graph[u][v]['weight'] += 1

    return the_graph



def extract_tags_from_org_files(org_files, the_graph=None, tag_regex="^\*\*\s+.+?\s+:(\S+):$") -> nx.Graph:
    logging.info("Extracting data from orgs")
    if the_graph is None:
        the_graph = nx.Graph()
    ORG_TAG_REGEX = regex.compile(tag_regex)

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

            e_tags = [x for x in tags[0].split(':') if x != '']
            e_tags = [TAG_NORM.sub("_", x.strip()) for x in e_tags]
            remaining = e_tags[:]
            [the_graph.add_node(x, count=0) for x in e_tags if x not in the_graph]

            #Add to dict:
            for tag in e_tags:
                if tag not in the_graph:
                    the_graph.add_node(tag, count=0)
                the_graph.nodes[tag]['count'] += 1

                remaining.remove(tag)
                edges_to_increment = [(tag,y) for y in remaining]
                for u,v in edges_to_increment:
                    if not the_graph.has_edge(u,v):
                        the_graph.add_edge(u,v, weight=0)
                    the_graph[u][v]['weight'] += 1

    return the_graph


def extract_tags_from_html_files(html_files, the_graph=None) -> nx.Graph:
    logging.info("Extracting data from htmls")
    if the_graph is None:
        the_graph = nx.Graph()

    for html in html_files:
        bkmks = open_and_extract_bookmarks(html)
        for bkmk in bkmks:
            remaining = list(bkmk.tags)
            [the_graph.add_node(x, count=0) for x in bkmk.tags if x not in the_graph]

            for tag in bkmk.tags:
                the_graph.nodes[tag]['count'] += 1

                remaining.remove(tag)
                edges_to_increment = [(tag,y) for y in remaining]
                for u,v in edges_to_increment:
                    if not the_graph.has_edge(u,v):
                        the_graph.add_edge(u,v, weight=0)
                    the_graph[u][v]['weight'] += 1

    return the_graph

def extract_tags_from_bookmark_files(bkmk_files, the_graph=None) -> nx.Graph:
    if the_graph is None:
        the_graph = nx.Graph()

    for bkmk_f in bkmk_files:
        bkmks = load_plain_file(bkmk_f)

        for bkmk in bkmks:
            tags          = bkmk.tags
            remaining     = tags[:]

            [the_graph.add_node(x, count=0) for x in tags if x not in the_graph]

            for tag in tags:
                the_graph.nodes[tag]['count'] += 1
                remaining.remove(tag)
                edges_to_increment = [(tag, y) for y in remaining]
                for u,v in edges_to_increment:
                    if not the_graph.has_edge(u,v):
                        the_graph.add_edge(u,v, weight=0)
                    the_graph[u][v]['weight'] += 1

    return the_graph


def read_substitutions(target: Union[str, List[str]], counts=True) -> Dict[str, List[str]]:
    """ Read a text file of the form (with counts):
    tag : num : sub : sub : sub....
    without counts:
    tag : sub : sub : ...
    returning a dict of {tag : [sub]}
    """
    raise DeprecationWarning("use bkmkorg.utils.tag.collection.TagFile")
