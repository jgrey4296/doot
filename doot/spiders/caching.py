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
from scrapy.dupefilters import RFPDupeFilter
from scrapy.exporters import XmlItemExporter
from scrapy.http import Headers, Response
from scrapy.http.request import Request
from scrapy.responsetypes import responsetypes
from scrapy.spiders import Spider
from scrapy.utils.httpobj import urlparse_cached
from w3lib.http import headers_dict_to_raw, headers_raw_to_dict


class CachePolicy:
    """
    Defines when cache's become invalid
    """

    def __init__(self, settings):
        self.ignore_schemes = settings.getlist("HTTPCACHE_IGNORE_SCHEMES")
        self.ignore_http_codes = [
            int(x) for x in settings.getlist("HTTPCACHE_IGNORE_HTTP_CODES")
        ]

    def should_cache_request(self, request):
        return urlparse_cached(request).scheme not in self.ignore_schemes

    def should_cache_response(self, response, request):
        return response.status not in self.ignore_http_codes

    def is_cached_response_fresh(self, cachedresponse, request):
        return True

    def is_cached_response_valid(self, cachedresponse, response, request):
        return True

class CacheStorage:
    """
    Defines how responses are stored and retrieved in the cache
    """

    def __init__(self, settings):
        self.cachedir        = settings["HTTPCACHE_DIR"]
        self.expiration_secs = settings.getint("HTTPCACHE_EXPIRATION_SECS")
        self.use_gzip        = settings.getbool("HTTPCACHE_GZIP")
        self._open           = gzip.open if self.use_gzip else open

    def open_spider(self, spider: Spider):
        logging.debug("Using filesystem cache storage in %s", self.cachedir, extra={"spider": spider},)
        self._fingerprinter = spider.crawler.request_fingerprinter

    def close_spider(self, spider):
        pass

    def retrieve_response(self, spider: Spider, request: Request):
        """Return response if present in cache, or None otherwise."""
        metadata       = self._read_meta(spider, request)
        if metadata is None:
            return  # not cached
        logging.debug("Reusing cached response")
        rpath          = self._get_request_path(spider, request)
        with self._open(rpath / "response_body", "rb") as f:
            body       = f.read()
        with self._open(rpath / "response_headers", "rb") as f:
            rawheaders = f.read()
        url            = metadata.get("response_url")
        status         = metadata["status"]
        headers        = Headers(headers_raw_to_dict(rawheaders))
        respcls        = responsetypes.from_args(headers=headers, url=url, body=body)
        response       = respcls(url=url, headers=headers, status=status, body=body)
        return response

    def store_response(self, spider: Spider, request: Request, response):
        """Store the given response in the cache."""
        rpath = self._get_request_path(spider, request)
        if not rpath.exists():
            rpath.mkdir(parents=True)
        metadata = {
            "url": request.url,
            "method": request.method,
            "status": response.status,
            "response_url": response.url,
            "timestamp": time(),
        }

        (rpath / "meta").write_bytes(repr(metadata).encode())
        (rpath / "pickled_meta").write_bytes(pickle.dumps(metadata, protocol=4))
        (rpath / "response_headers").write_bytes(headers_dict_to_raw(response.headers))
        (rpath / "response_body").write_bytes(response.body)
        (rpath / "request_headers").write_bytes(headers_dict_to_raw(request.headers))
        (rpath / "request_body").write_bytes(request.body)

    def _get_request_path(self, spider: Spider, request: Request) -> pl.Path:
        key = self._fingerprinter.fingerprint(request).hex()
        return pl.Path(self.cachedir, spider.name, key[0:2], key)

    def _read_meta(self, spider: Spider, request: Request):
        rpath = self._get_request_path(spider, request)
        metapath = rpath / "pickled_meta"
        if not metapath.exists():
            return  # not found
        mtime = metapath.stat().st_mtime
        if 0 < self.expiration_secs < time() - mtime:
            return  # expired
        with self._open(metapath, "rb") as f:
            return pickle.load(f)


class CacheDupeFilter(RFPDupeFilter):
    """
    Filter Requests by cache status

    """

    def request_seen(self, request):
        logging.debug("Request Seen: %s", request.url)
        # fp = self.request_fingerprint(request)
        return super().request_seen(request)
