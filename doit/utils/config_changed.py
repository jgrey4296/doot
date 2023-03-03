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


class ConfigChanged:
    """check if passed config was modified
    @var config (str) or (dict)
    @var encoder (json.JSONEncoder) Encoder used to convert non-default values.
    """

    def __init__(self, config, encoder=None):
        self.config = config
        self.config_digest = None
        self.encoder = encoder

    def _calc_digest(self):
        if isinstance(self.config, str):
            return self.config
        elif isinstance(self.config, dict):
            data = json.dumps(self.config, sort_keys=True, cls=self.encoder)
            byte_data = data.encode("utf-8")
            return hashlib.md5(byte_data).hexdigest()
        else:
            msg = ('Invalid type of config_changed parameter got %s,'
                   ' must be string or dict')
            raise Exception(msg % (type(self.config),))

    def configure_task(self, task):
        task.value_savers.append(lambda: {'_config_changed': self.config_digest})

    def __call__(self, task, values):
        """return True if config values are UNCHANGED"""
        self.config_digest = self._calc_digest()
        last_success = values.get('_config_changed')
        if last_success is None:
            return False
        return (last_success == self.config_digest)
