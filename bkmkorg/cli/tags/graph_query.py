#!/usr/bin/env python3
"""
    Simple CLI for querying a tag graph

input: edgelist::file, query::List[str]
returns: connections::Set[str]


"""
##-- imports
from __future__ import annotations
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic
import argparse
import logging as root_logger
import networkx as nx

import pathlib as pl
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))
parser.add_argument('--edgelist', default="/Volumes/documents/github/writing/resources/cron_reports/tags.edgelist")
parser.add_argument('tags', nargs="*")
##-- end argparse

def main():
    args = parser.parse_args()
    # Load the edgelist
    args.edgelist = pl.Path(args.edgelist).expanduser().resolve()

    graph = nx.read_weighted_edgelist(str(args.edgelist))

    frontier = set()
    assert(all([x in graph for x in args.tags]))
    # query for each tag
    for tag in args.tags:
        current   = graph[tag]
        connected = set(current.keys())

        if not bool(frontier):
            frontier.update(connected)
        else:
            frontier.intersection_update(connected)


    # Return available connections
    print("\n".join(frontier))

##-- ifmain
if __name__ == "__main__":
    logging.info("Starting ")

##-- end ifmain
