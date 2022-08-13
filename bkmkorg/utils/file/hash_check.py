#!/usr/bin/env python
##-- imports
from __future__ import annotations

import logging as root_logger
import pathlib as pl
from hashlib import sha256
##-- end imports

logging = root_logger.getLogger(__name__)

def file_to_hash(filename:pl.Path):
    with open(filename, 'rb') as f:
        return sha256(f.read()).hexdigest()

def hash_all(files:list[pl.Path]):
    """
    Map hashes to files,
    plus hashes with more than one image
    """
    assert(isinstance(files, list))
    assert(all([isinstance(x, pl.Path) for x in files]))
    assert(all([x.is_file() for x in files]))

    hash_dict = {}
    conflicts = {}
    update_num = int(len(files) / 100)
    count = 0
    for i,x in enumerate(files):
        if i % update_num == 0:
            logging.info("{} / 100".format(count))
            count += 1
        the_hash = file_to_hash(x)
        if the_hash not in hash_dict:
            hash_dict[the_hash] = []
        hash_dict[the_hash].append(x)
        if len(hash_dict[the_hash]) > 1:
            conflicts[the_hash] = len(hash_dict[the_hash])

    return (hash_dict, conflicts)

def find_missing(library:list[pl.Path], others:list[pl.Path]):
    # TODO: handle library hashes that already have a conflict
    library_hash, conflicts = hash_all(library)
    missing = []
    update_num = int(len(others) / 100)
    count = 0
    for i,x in enumerate(others):
        if i % update_num == 0:
            logging.info("{} / 100".format(count))
            count += 1
        the_hash = file_to_hash(x)
        if the_hash not in library_hash:
            missing.append(x)
    return missing
