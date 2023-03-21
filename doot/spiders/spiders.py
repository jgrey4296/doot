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

import gzip
import pickle
from time import time

import scrapy
from itemadapter import ItemAdapter, is_item
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.exporters import XmlItemExporter
from scrapy.http import Headers, Response
from scrapy.http.request import Request
from scrapy.responsetypes import responsetypes
from scrapy.spiders import Spider
from scrapy.utils.httpobj import urlparse_cached
from w3lib.http import headers_dict_to_raw, headers_raw_to_dict

class DootBasicSpider(scrapy.Spider):
    """
    Basic Doot Spider that stores locs and its parent task
    """

    def __init__(self, name  =None, locs=None, urls=None, domains=None, task=None):
        super().__init__(name)
        self.locs            = locs
        self.task            = task
        self.start_urls      = urls
        self.allowed_domains = domains or []

    def parse(self, response):
        page     = response.url.split("/")[-2]
        filename = self.locs.data / f"{page}.html"
        pl.Path(filename).write_bytes(response.body)
        yield { "data": response.url }
