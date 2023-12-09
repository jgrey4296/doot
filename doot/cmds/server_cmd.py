#!/usr/bin/env python3
"""

"""
##-- imports
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

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging
printer = logmod.getLogger("doot._printer")
from flask import Flask, request
import doot
from doot._abstract import Command_i

app = Flask("basic")

# From https://stackoverflow.com/questions/63902300
class BasicServer(Command_i):
    """
    a test doot command
    """
    name            = 'BasicServer'
    doc_purpose     = "A Really Simple Https Flask Server"
    doc_description = ""
    doc_usage       = ""
    cmd_options     = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def param_specs(self) -> list:
        return super().param_specs + []

    def __call__(self, tasks:TomlGuard, plugins:TomlGuard):
        pass
        # app.run(port=8000, debug=True, ssl_context="adhoc")

@app.route('/', methods=["GET", "POST"])
def index():
    # https://improveandrepeat.com/2022/03/python-friday-112-how-to-use-tweepy-in-flask/
    # args               = request.args
    logging.info(request.url)
    return "nothing"
