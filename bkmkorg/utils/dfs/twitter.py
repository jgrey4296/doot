from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

import logging as root_logger
from os import listdir
from os.path import isdir, isfile, join, splitext

import networkx as nx

logging = root_logger.getLogger(__name__)

def dfs_edge(graph, edge) -> Set[str]:
    """ Getting non-quote tweets """
    found = set()
    queue = [edge]

    while bool(queue):
        current = queue.pop(0)
        l, r = current
        if l in found and r in found:
            continue

        found.add(l)
        found.add(r)
        to_add = [(l, x) for x in graph.adj[l] if graph.adj[l][x]['type'] == "reply"]
        to_add += [(r, x) for x in graph.adj[r] if graph.adj[r][x]['type'] == "reply"]

        if len(to_add) > 500:
            breakpoint()
        queue += to_add

    return found

def dfs_for_components(tweet_graph:'TwitterGraph') -> List[Set[str]]:
    """ DFS a graph for all connected components """
    # Convert to undirected graph
    graph : nx.Graph = tweet_graph.to_undirected()

    # DFS for components
    components   = []
    edge_set     = set(graph.edges)
    discovered   = set()
    logging.info("DFS on Components: {}".format(len(edge_set)))
    count        = 0
    log_on_count = len(edge_set) * 0.1
    while bool(edge_set):
        count += 1
        current = edge_set.pop()
        l, r = current
        if l in discovered and r in discovered:
            continue
        # Get connected edges (direct replies only, not quotes)
        connected_ids = dfs_edge(graph, current)
        # Then get quotes
        quotes = [y for x in connected_ids for y in graph.adj[x] if graph.adj[x][y]['type'] == 'quote']
        while bool(quotes):
            current = quotes.pop()
            connected_ids.add(current)
            quotes += [y for y in graph.adj[current]
                       if graph.adj[current][y]['type'] == 'quote' and y not in connected_ids]

        components.append(connected_ids)
        discovered.update(connected_ids)
        if count > log_on_count:
            count = 0
            logging.info("Edge Set Size: {}".format(len(edge_set)))

    logging.info("Found {} components".format(len(components)))
    return components

def dfs_chains(graph, roots):
    results = []
    queue = [[x] for x in roots]
    discovered = set()
    while bool(queue):
        path = queue.pop()
        discovered.update(path)
        if path[-1] not in graph:
            results.append(path)
            continue
        edges = [x for x in graph[path[-1]].keys() if x not in discovered]
        if not bool(edges):
            results.append(path)
        else:
            queue += [path + [x] for x in edges]

    return results
