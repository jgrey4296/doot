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
from bkmkorg.io.reader.netscape import open_and_extract_bookmarks

logging = root_logger.getLogger(__name__)

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




