#!~/anaconda/envs/bookmark/bin/python

"""
Tagset Utilities

"""
import logging as root_logger
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import networkx as nx
import regex
from bkmkorg.io.import.netscape import open_and_extract_bookmarks

logging = root_logger.getLogger(__name__)

def extract_tags_from_bibtex(db, the_graph=None):
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
        e_tags = entry['tags']
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



def extract_tags_from_org_files(org_files, the_graph=None, tag_regex="^\*\*\s+.+?\s+:(\S+):$"):
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


def extract_tags_from_html_files(html_files, the_graph=None):
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
def combine_all_tags(graph_list: List['Graph']) -> Dict[str, int]:
    logging.info("Combining tags")
    assert(isinstance(graph_list, list))
    assert(all([isinstance(x, nx.Graph) for x in graph_list]))
    all_tags = {}

    for graph in graph_list:
        for tag in graph.nodes:
            if tag not in all_tags:
                all_tags[tag] = 0
            all_tags[tag] += graph.nodes[tag]['count']

    return all_tags




def write_tags(all_tags: Union['Graph', Dict[str, int]], output_target):
    if isinstance(all_tags, nx.Graph):
        tag_str = ["{} : {}".format(k, all_tags.nodes[k]['count']) for k in all_tags.nodes]
    elif isinstance(all_tags, dict):
        tag_str = ["{} : {}".format(k, v) for k, v in all_tags.items()]
    else:
        raise Exception("Unrecognised write tag object")

    with open("{}.tags".format(output_target), 'w') as f:
        logging.info("Writing Tag Counts")
        f.write("\n".join(tag_str))







