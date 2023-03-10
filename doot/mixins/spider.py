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

##-- imports
from importlib.resources import files
##-- end imports

import tomler
import doot
from doot.spiders.crawler import CrawlerProcessFix

default_toml           = tomler.load(files("doot.__templates") / "spider_toml").flatten_on().spiders().get_table()
spider_settings        = doot.config.flatten_on().spiders().get_table()

settings_with_defaults = default_toml.copy()
settings_with_defaults.update(spider_settings)

class SpiderMixin:
    """
    Run a scrapy spider either with default doot settings,
    or passed in toml data
    """

    def run_spider(self, name:str, spider:type, urls:list, settings=None):
        logging.info("Running spider: %s", name)
        match settings:
            case None:
                settings = settings_with_defaults
            case dict() | tomler.Tomler():
                pass
            case False:
                settings = default_toml

        self.crawler = CrawlerProcessFix(settings=settings, install_root_handler=False)
        self.crawler.crawl(spider, name=name, locs=self.locs, urls=urls)
        self.crawler.start()
