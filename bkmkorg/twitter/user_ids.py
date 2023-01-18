#/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import json
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
import twitter

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def get_user_identities(users_file:pl.Path, twit, users) -> Dict[str, Any]:
    """ Get all user identities from twitter """
    logging.info("Getting user identities")
    total_users = {}
    user_queue  = list(users)
    if users_file.exists():
        with open(users_file,'r') as f:
            total_users.update({x['id_str'] : x for x in  json.load(f, strict=False)})

        users -= total_users.keys()
        logging.info("Already retrieved %s, %s remaining", len(total_users), len(users))
        user_queue = list(users)

    while bool(user_queue):
        current = user_queue[:100]
        user_queue = user_queue[100:]

        try:
            data = twit.UsersLookup(user_id=current)
            logging.info("Retrieved: %s", len(data))
            new_users = [json.loads(x.AsJsonString()) for x in data]
            total_users.update({x['id_str'] : x for x in new_users})

        except twitter.error.TwitterError as err:
            logging.info("Does not exist: %s", current)

    with open(users_file, 'w') as f:
        json.dump(list(total_users.values()), f, indent=4)

    return total_users
