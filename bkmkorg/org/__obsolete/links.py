#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
import re
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

##-- consts

DEFAULT_PATTERN = re.compile(r"(.*?\[+)/Users/johngrey/Desktop/twitter/orgs/(.+?)(\]\[.+)$")
PERMALINK       = re.compile(r".*?:PERMALINK: *\[\[(.+?)\]\[")
LINK            = re.compile(r".*\[\[(.+?)\]\[")
##-- end consts

def map_media(org_file) -> dict:
    """
    for an org, get a mapping of {tweet : [media_links]}
    """
    with open(org_file, 'r') as f:
        lines = f.readlines()

    media = {}
    current_tweet = None
    for line in lines:
        the_match = PERMALINK.match(line)
        if the_match:
            current_tweet = the_match[1]
            continue
        the_match = LINK.match(line)
        if the_match:
            if current_tweet not in media:
                media[current_tweet] = []
            media[current_tweet].append(the_match[1])

    return media

def make_relative_media_links(org_file, pattern):
    """
    for an org file, back it up,
    then retarget all file paths to be relative
    """
    # read file
    logging.debug("Org file: %s \n %s", org_file, org_file + "_backup")
    with open(org_file, 'r') as f:
        lines = f.readlines()
    # duplicate file
    with open(org_file.with_suffix(".org.backup"), 'w') as f:
        f.write("\n".join(lines))

    # transform file
    new_target = org_file.parent
    retargeted = []
    for line in lines:
        maybe_match = pattern.match(line)
        if not maybe_match:
            retargeted.append(line)
        else:
            # transform line
            new_target_t = new_target /  maybe_match[2]
            newline = pattern.sub(r"\1{}\3".format(new_target_t), line)
            retargeted.append(newline)

    # write file
    with open(org_file, 'w') as f:
        f.write("\n".join([x for x in retargeted]))
