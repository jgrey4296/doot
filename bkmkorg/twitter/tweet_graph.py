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

logging = logmod.getLogger(__name__)

@dataclass
class TwitterGraph:
    """
    A Directed Graph of tweets, built from a directory of tweet jsons
    """
    graph : nx.DiGraph = field(default_factory=nx.DiGraph)

    def add_tweet(self, tweet:dict, source:pl.Path):
        """
        Add tweet data to the graph
        reply_id -> tweet_id so threads are root -> reply -> reply -> reply -> leaf
        tweet_id -> quoted_id so quotes are tweet -> quote -> quote...
        """
        tweet_id = tweet.get('id_str', None)
        user_id  = tweet.get('user', {}).get('id_str', None)

        if tweet_id is None:
            return

        if tweet_id not in self.graph:
            self.graph.add_node(tweet_id)

        self.graph.nodes[tweet_id].update({"source_file":str(source), "user":user_id})

        match tweet:
            case {'in_reply_to_status_id_str': None, 'is_quote_status': False}:
                pass
            case { 'in_reply_to_status_id_str': str() as reply_id, 'in_reply_to_user_id_str': reply_user, 'is_quote_status': False }:
                self.graph.add_node(reply_id, user=reply_user, source_file=str(source))
                self.graph.add_edge(reply_id, tweet_id, type="reply")
            case { 'in_reply_to_status_id_str': str() as reply_id, 'in_reply_to_user_id_str': reply_user, 'quoted_status_id_str': str() as quoted_id }:
                self.graph.add_node(reply_id, user=reply_user, source_file=str(source))
                quoted_user = tweet.get('quoted_status', {}).get('user', {}).get('id_str', None)
                if quoted_user is not None:
                    self.graph.add_node(quoted_id, user=quoted_user, source_file=str(source))

                self.graph.add_edge(reply_id, tweet_id, type="reply")
                self.graph.add_edge(tweet_id, quoted_id, type="quote")
            case { 'quoted_status_id_str': str() as quoted_id }:
                quoted_user = tweet.get('quoted_status', {}).get('user', {}).get('id_str', None)
                if quoted_user is not None:
                    self.graph.add_node(quoted_id, user=quoted_user, source_file=str(source))

                self.graph.add_edge(tweet_id, quoted_id, type="quote")

    def components(self):
        logging.info("Getting Components for Graph")
        undir_graph : nx.Graph = nx.Graph([x for x in self.graph.edges if self.graph.get_edge_data(*x)['type'] == 'reply'])
        components             = list(nx.connected_components(undir_graph))
        logging.info("Components Retrieved, getting quotes")
        found = set()
        for component in components:
            quotes = self.get_quotes(*component)
            component.update(quotes)
            found.update(component)

        rest = set(undir_graph.nodes) - found

        return components, rest

    def get_quotes(self, *srcs: str):
        if not bool(srcs):
            return [ y for x,y in self.graph.edges if self.graph.get_edge_data(x,y).get('type', "n/a") == 'quote']

        queue      = [x for id_s in srcs for x in self.graph[id_s] if self.graph.get_edge_data(id_s, x)['type'] == "quote"]
        discovered = set()
        while bool(queue):
            quoted_id = queue.pop(0)
            if quoted_id in discovered:
                continue
            discovered.add(quoted_id)
            queue += [x for x in self.graph[quoted_id] if self.graph.get_edge_data(quoted_id, x)['type'] == "quote"]

        return discovered

    def roots(self):
        reply_graph : nx.DiGraph = self.graph.edge_subgraph([x for x in self.graph.edges if self.graph.get_edge_data(*x).get('type', "n/a") == 'reply'])
        return [x for x,y in reply_graph.in_degree if y == 0]

    def reply_chains(self, roots) -> list[list[str]]:
        reply_graph : nx.DiGraph = self.graph.edge_subgraph([x for x in self.graph.edges if self.graph.get_edge_data(*x).get('type', "n/a") == 'reply'])

        discovered = set()
        chains     = []
        current    = []
        last       = []
        for root in roots:
            for l, r, kind in nx.dfs_labeled_edges(reply_graph, root):
                discovered.add(r)
                match kind:
                    case 'forward':
                        current.append(r)
                    case 'reverse' if not all(x in last for x in current):
                        chains.append(current[:])
                        current.pop()
                        last = current[:]
                    case 'reverse':
                        current.pop()

        remaining = [x for x in set(reply_graph.nodes) - discovered]
        return chains, remaining
