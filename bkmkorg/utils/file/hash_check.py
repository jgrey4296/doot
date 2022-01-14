#!/usr/bin/env python
import logging as root_logger
from hashlib import sha256
from os import listdir, mkdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

logging = root_logger.getLogger(__name__)

def file_to_hash(filename):
    with open(filename, 'rb') as f:
        return sha256(f.read()).hexdigest()

def hash_all(files):
    """
    Map hashes to files,
    plus hashes with more than one image
    """
    assert(isinstance(files, list))
    assert(all([isfile(x) for x in files]))

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

def find_missing(library, others):
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
