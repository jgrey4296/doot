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
from urllib.parse import urlparse

default_toml           = tomler.load(files("doot.__templates") / "spider_toml").flatten_on().spiders().get_table()
spider_settings        = doot.config.flatten_on().spiders().get_table()

settings_with_defaults = default_toml.copy()
settings_with_defaults.update(spider_settings)

class SpiderMixin:
    """
    Run a scrapy spider either with default doot settings,
    or passed in toml data
    """

    def _urlparse(self, url:str):
        return urlparse(url)

    def run_spider(self, name:str, spider:type, urls:list, settings=None, auto_limit=True, scrapy_log=False):
        """
        auto_limit = True -> auto set allowed_domains to the domains of initial urls
        """
        logging.info("Running spider: %s : %s : %s : %s", name, spider, urls, settings)
        merged = settings_with_defaults
        match settings:
            case None:
                pass
            case dict() if bool(settings):
                merged.update(settings)
            case tomler.Tomler():
                merged.update(dict(settings))
            case [dict() as val]:
                merged = val

        allowed_domains = [self._urlparse(x).netloc for x in urls] if auto_limit else []
        logging.debug("----- Building Crawler")
        self.crawler    = CrawlerProcessFix(settings=merged, install_root_handler=scrapy_log)
        self.crawler.crawl(spider,
                           name=name,
                           locs=self.locs,
                           urls=urls,
                           domains=allowed_domains,
                           task=self)
        logging.debug("------ Starting Crawl")
        self.crawler.start()
        logging.debug("------ Crawl Finished")
