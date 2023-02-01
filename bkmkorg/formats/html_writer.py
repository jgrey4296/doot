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

from bs4 import BeautifulSoup

class HtmlWriter:
    """
    Html Equivalent to org_builder
    """

    def __init__(self):
        self.soup = BeautifulSoup()

    def _header(self):
        pass

    def add_paragraph(self):
        pass

    def add_meta(self):
        pass

    def add_link(self):
        pass

    def add_style(self):
        pass
