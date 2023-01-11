#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import logging as root_logger
import pathlib as pl
from datetime import datetime
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from collections import defaultdict
import regex as re
##-- end imports

logging = root_logger.getLogger(__name__)

def collect_files(targets:list[str|pl.Path]) -> dict:
    """ DFS targets, collecting files into their types """
    logging.info("Processing Files: %s", targets)

    processed      = set([])
    remaining_dirs = [pl.Path(x).expanduser().resolve() for x in targets]
    unrecognised   = set([])

    grouped_results = defaultdict(set)

    while bool(remaining_dirs):
        target = remaining_dirs.pop(0)
        assert(target.exists())
        if target in processed:
            continue
        processed.add(target)
        if target.is_file():
            grouped_results[target.suffix.lower()].add(target)
        else:
            assert(target.is_dir()), target
            remaining_dirs += [x for x in target.iterdir()]

    return grouped_results

def get_data_files(initial:str|pl.Path, ext=None) -> list[str]:
    """
    DFS, Getting all files of an extension
    """
    logging.info("Getting Data Files")
    ext = ext or []

    if not isinstance(ext, list):
        ext = [ext]
    if not isinstance(initial, list):
        initial = [initial]

    unrecognised = set()
    files        = []
    queue        = [pl.Path(x).expanduser().resolve() for x in initial]
    while bool(queue):
        current : pl.Path = queue.pop(0)
        assert(current.exists())
        ftype             = current.suffix.lower()
        match_type        = not bool(ext) or ftype in ext
        missing_type      = ftype not in unrecognised and ftype != ""

        if current.is_file() and match_type:
            files.append(current)
        elif current.is_file() and not match_type and missing_type:
            unrecognised.add(ftype)
        elif current.is_dir():
            queue += [x for x in current.iterdir()]


    logging.info("Found %s %s files", len(files), ext)
    if bool(unrecognised):
        logging.warning("Unrecognized file types: %s", unrecognised)
    return files
