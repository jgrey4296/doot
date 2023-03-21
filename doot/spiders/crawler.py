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

import scrapy
from scrapy import signals
from scrapy.utils.log import log_scrapy_info
from itemadapter import is_item, ItemAdapter
from scrapy.utils.httpobj import urlparse_cached
import gzip
import pickle
from time import time
from w3lib.http import headers_dict_to_raw, headers_raw_to_dict

import scrapy
from scrapy.http import Headers, Response
from scrapy.http.request import Request
from scrapy.responsetypes import responsetypes
from scrapy.spiders import Spider
from scrapy.utils.httpobj import urlparse_cached
from itemadapter import ItemAdapter
from scrapy.exporters import XmlItemExporter
from scrapy.crawler import CrawlerProcess

class SimpleFilter(logmod.Filter):

    def filter(self, record):
        record.args = {x:y.replace("\n"," ") for x,y in record.args.items()}
        record.msg  = record.msg.replace("\n", " ")
        return True

class CrawlerProcessFix(CrawlerProcess):
    """
    Modified scrapy.crawler.CrawlerProcess
    that doesn't call `configure_logging`, and so doesnt mess up
    existing loggers
    """

    def __init__(self, settings=None, install_root_handler=False):
        if not install_root_handler:
            super(CrawlerProcess, self).__init__(settings)
        else:
            logging.warning("Using standard scrapy crawler, will override log settings")
            super().__init__(settings, install_root_handler=install_root_handler)

        # skipped -> configure_logging(self.settings, install_root_handler)
        # log_scrapy_info(self.settings)
        logging.debug("CrawlerProcess Settings: %s", list(self.settings._to_dict().keys()))
        self._initialized_reactor = False
        filter_nls = SimpleFilter()
        for logName in [f"scrapy.{x}" for x in dir(scrapy) if "__" not in x]:
            logmod.getLogger(logName).addFilter(filter_nls)
        logmod.getLogger("scrapy.statscollector").addFilter(filter_nls)
