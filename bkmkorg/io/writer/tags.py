#!/usr/bin/env python
"""
Tagset Writing

"""
import logging as root_logger
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import networkx as nx
import regex
from bkmkorg.io.reader.netscape import open_and_extract_bookmarks

logging = root_logger.getLogger(__name__)

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
