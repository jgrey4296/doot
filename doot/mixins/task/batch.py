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
printer = logmod.getLogger("doot._printer")
##-- end logging
from time import sleep
import doot

batch_size       = doot.config.on_fail(10, int).settings.tasks.batch.size()
batches_max      = doot.config.on_fail(-1,    int).settings.tasks.batch.max()
sleep_batch      = doot.config.on_fail(2.0,   int|float).settings.tasks.sleep.batch()
sleep_notify     = doot.config.on_fail(False, bool).settings.general.notify.sleep()

class BatchMixin:
    """
    A Mixin to enable running batches of *subtasks* with
    some sleep time

    'run_batches' controls batching bookkeeping,
    'batch' is the actual action
    """

    batch_count       = 0

    def run_batches(self, *batches, reset=True, fn=None, **kwargs):
        """
        handles batch bookkeeping

        defaults to self.batch, but can pass in a function
        """
        if reset:
            self._reset_batch_count()
        fn = fn or self.batch

        result = []
        for data in batches:
            match data:
                case [*items]:
                    batch_data = [x for x in items if x is not None]
                    if not bool(batch_data):
                        continue
                    self.log(f"Batch: {self.batch_count} : ({len(batch_data)})")
                case _:
                    batch_data = data

            batch_result =  fn(batch_data, **kwargs)
            match batch_result:
                case None:
                    pass
                case list():
                    result += batch_result
                case set():
                    result += list(batch_result)
                case _:
                    result.append(batch_result)

            self.batch_count += 1
            if -1 < batches_max < self.batch_count:
                self.log("Max Batch Hit")
                return
            if sleep_notify:
                self.log("Sleep Batch")
            sleep(sleep_batch)

        return result

    def batch(self, data, **kwargs):
        """ Override to implement what a batch does """
        raise NotImplementedError()

    def chunk(self, iterable, n:int=None, *, incomplete='fill', fillvalue=None):
        """Collect data into non-overlapping fixed-length chunks or blocks
        from https://docs.python.org/3/library/itertools.html
         grouper('ABCDEFG', 3, fillvalue='x') --> ABC DEF Gxx
         grouper('ABCDEFG', 3, incomplete='strict') --> ABC DEF ValueError
         grouper('ABCDEFG', 3, incomplete='ignore') --> ABC DEF
        """
        # TODO replace with more-itertools
        n    = n or batch_size
        args = [iter(iterable)] * n
        if incomplete == 'fill':
            return itz.zip_longest(*args, fillvalue=fillvalue)
        if incomplete == 'strict':
            return zip(*args, strict=True)
        if incomplete == 'ignore':
            return zip(*args)
        else:
            raise ValueError('Expected fill, strict, or ignore')

    def _reset_batch_count(self):
        self.batch_count = 0
