#!/usr/bin/env python3
"""

"""
##-- imports

##-- end imports

##-- default imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end default imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


def process():
    # Collect the media files
    logging.info("Collecting media from: %s", ",".join(library))
    queue = library[:]
    media = defaultdict(lambda: [])
    while bool(queue):
        current = queue.pop(0)
        if isfile(current) and splitext(current)[1] == ".mp4":
            media[split(current)[1]].append(current)
        elif isdir(current):
            queue += [join(current, x) for x in listdir(current) if x != ".git"]

    logging.info("Found %s  media", len(media))

    # Get variants:
    logging.info("Reading variant lists from: %s ", target)
    with open(target, 'r') as f:
        var_text = f.read()
    variants_list = json.loads(var_text)


    logging.info("Building Equivalency lists")
    equivalent_files = []
    for var_url_list in variants_list:
        filenames = [split(x)[1] for x in var_url_list]
        existing = [x for x in filenames if x in media]
        if bool(existing):
            equivalent_files.append(existing)

    logging.info("Found %s equivalents", len(equivalent_files))

    logging.info("Keeping Not-smallest files")
    for equiv_list in equivalent_files:
        paths = [media[x] for x in equiv_list]
        if len(paths) == 1:
            continue

        grouped_by_prefix = defaultdict(lambda: [])

        for group in paths:
            for a_path in group:
                prefix = split(a_path)[0]
                grouped_by_prefix[prefix].append(a_path)

        logging.info("Working with %s prefix groups", len(grouped_by_prefix))
        for prefix_group in grouped_by_prefix.values():
            logging.info("--------------------")
            sized = sorted([(getsize(x), x) for x in prefix_group if exists(x)])
            # keep the largest, to downsize later
            largest = sized.pop()
            logging.info("Keeping: %s", str(largest))
            # Move the rest
            for s, x in sized:
                logging.info("Trashing: %s", s)
                move_file(x, trash, args.real)
