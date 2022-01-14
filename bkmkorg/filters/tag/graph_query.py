#!/usr/bin/env python3
"""
    Simple CLI for querying a tag graph

input: edgelist::file, query::List[str]
returns: connections::Set[str]


"""
##############################
# IMPORTS
####################
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic
import argparse
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
import networkx as nx

# Setup root_logger:
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
# CONSTANTS
####################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))
parser.add_argument('--edgelist', default="/Volumes/documents/github/writing/resources/cron_reports/tags.edgelist")
parser.add_argument('tags', nargs="*")

def main():
    args = parser.parse_args()
    # Load the edgelist
    args.edgelist = abspath(expanduser(args.edgelist))

    graph = nx.read_weighted_edgelist(args.edgelist)

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

########################################
if __name__ == "__main__":
    logging.info("Starting ")
