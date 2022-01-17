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

from bkmkorg.utils.dfs.files import get_data_files

logging = root_logger.getLogger(__name__)

@dataclass
class TwitterGraph:
    """
    A Directed Graph of tweets, built from a directory of tweet jsons
    """
    graph : nx.DiGraph

    @staticmethod
    def build(json_dir):
        """ Create a graph of tweet replies and quotes """
        logging.info("Assembling threads graph from: {}".format(json_dir))
        json_files = get_data_files(json_dir, ext=".json")
        di_graph = nx.DiGraph()
        for jfile in json_files:
            # load in each json,
            with open(jfile, 'r') as f:
                data = json.load(f, strict=False)

            # construct connection graph
            for entry in data:
                # get tweet id, reply_id, quote_id
                tweet_id = entry['id_str']
                di_graph.add_node(tweet_id, source_file=jfile)

                if 'in_reply_to_status_id_str' in entry and entry['in_reply_to_status_id_str']:
                    # link tweets
                    di_graph.add_edge(tweet_id,
                                    str(entry['in_reply_to_status_id_str']),
                                    type="reply")

                if 'quoted_status_id_str' in entry and entry['quoted_status_id_str']:
                    di_graph.add_edge(tweet_id,
                                    str(entry['quoted_status_id_str']),
                                    type="quote")

        return TwitterGraph(di_graph)


    def get_quoters(self, id_s: str):
        quoter_edges = [x for x in self.graph[id_s] if self.graph[id_s][x] == "quote"]
        discovered = set()
        while bool(quoter_edges):
            quoter_id = quoter_edges.pop(0)
            discovered.add(quoter_id)
            additional_quotes = [x for x in self.graph[quoter_id] if self.graph[quoter_id][x] == "quote"]
            quoter_edges += [x not in discovered for x in additional_quotes]

        return discovered


    def to_undirected(self):
        return nx.Graph(self.graph)
