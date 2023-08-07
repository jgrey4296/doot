#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from time import sleep
import requests


def expander(current):
    # header = {'user-agent': args.agent}
    try:
        response = requests.head(current, allow_redirects=True, timeout=2, headers=header)
        if response.ok:
            expanded[current] = response.url
        else:
            expanded[current] = response.status_code

        return "{} |%| {}".format(current, args.separator, expanded[current])
    except Exception as err:
        cmd    = 'say -v Moira -r 50 "Error"'
        system(cmd)
        expanded[current] = f"400.1 : {str(err)}"
        logging.info("Error: %s", str(err))
