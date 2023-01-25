#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref
from time import sleep

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
FIFTEEN_MINUTES = 60 * 15
CHARWIDTH       = 80
##-- end consts

#download friend list

def get_friends(twit, id_s=None):
    """ Given a twitter client, get my friends (ie: people I follow)
    friends/ids returns up to 5000, 15 times in 15 minutes
    """
    logging.info("Getting friends for: %s, type: %s", id_s, type(id_s))
    #Gives up to 5000
    if id_s is not None:
        response = twit.friends.ids(user_id=id_s, stringify_ids="true")
    else:
        response = twit.friends.ids(stringify_ids="true")
    logging.info("Response length: %s", len(response['ids']))
    return response['ids']

def get_users(twit, ids=None, writer=None, backup=None|pl.Path):
    """ Given a list of users, split into 100 user chunks,
    then GET users/lookup for them
    """
    batch_size = 100
    rate_limit = 300
    backup_file = backup.with_suffix(".retrieved")
    #load the backup
    already_done = set()
    if backup_file.exists():
        logging.info("Retrieving processed record")
        with open(backup_file, 'r') as f:
            already_done = set(f.read().split('\n'))
    ids_set = list(set(ids).difference(already_done))
    chunked = [ids_set[x:x+batch_size] for x in range(0, len(ids_set), batch_size)]
    logging.info("After filtering, chunking %s into %s", len(ids), len(chunked))

    loop_count = 0
    for i, chunk in enumerate(chunked):
        logging.info("Chunk %s", i)
        #request
        returned_data = twit.users.lookup(user_id=",".join(chunk))
        #parse data
        parsed_data = [user_obj_to_tuple(x) for x in returned_data]
        #call writer
        writer(parsed_data)
        #backup
        with open(backup_file, 'a') as f:
            f.write("\n".join(chunk))

        if loop_count < rate_limit:
            loop_count += 1
            sleep(5)
        else:
            loop_count = 0
            logging.info("Sleeping")
            sleep(FIFTEEN_MINUTES)

def init_file(filename:pl.Path):
    if filename.exists():
        return
    with open(filename, 'a') as f:
        f.write("| User ID | Username | Tags | Verified |  Description|\n")
        f.write("|----|\n")

def append_to_file(filename:pl.Path, data):
    """ Append data to a given filename """
    with open(filename, 'a') as f:
        for user_str, username, verified, description in data:
            safe_desc = textwrap.wrap(description.replace('|',''), CHARWIDTH)
            if not bool(safe_desc):
                safe_desc = [description]
            f.write("| {} | {} |  | {} | {} |\n".format(user_str,
                                                        username,
                                                        verified,
                                                        safe_desc[0]))
            for subline in safe_desc[1:]:
                f.write("| | | | | {} |\n".format(subline))
            f.write ("|-----|\n")

def user_obj_to_tuple(user_obj):
    id_str   = user_obj['id_str']
    name     = user_obj['screen_name']
    verified = user_obj['verified']
    desc     = user_obj['description']
    return (id_str, name, verified, desc)
