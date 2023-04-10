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

import datetime
import scrapy
from scrapy import signals
from itemadapter import is_item, ItemAdapter
from scrapy.utils.httpobj import urlparse_cached
import gzip
import pickle
from time import time
from w3lib.http import headers_dict_to_raw, headers_raw_to_dict
from bs4 import BeautifulSoup
from urllib.parse import urlparse

import scrapy
from scrapy.http import Headers, Response
from scrapy.http.request import Request
from scrapy.responsetypes import responsetypes
from scrapy.spiders import Spider
from scrapy.utils.httpobj import urlparse_cached
from itemadapter import ItemAdapter
from scrapy.exporters import XmlItemExporter
from scrapy.crawler import CrawlerProcess

# available in scrapy.exporters:
# XmlItemExporter(file, item_element='item', root_element='items', **kwargs)
# CsvItemExporter(file, include_headers_line=True, join_multivalued=',', errors=None, **kwargs)
# PickleItemExporter(file, protocol=0, **kwargs)
# PprintItemExporter(file, **kwargs)
# JsonItemExporter(file, **kwargs)
# JsonLinesItemExporter(file, **kwargs)

class ItemData(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class SimpleXMLExporter:
    """
    """

    def open_spider(self, spider):
        self.items = []

    def close_spider(self, spider):
        with open(spider.locs.build / "results.xml", "wb") as f:
            exporter = XmlItemExporter(f)
            exporter.start_exporting()
            for item in self.items:
                exporter.export_item(item)
            exporter.finish_exporting()

    def process_item(self, item, spider):
        self.items.append(item)
        return item

class RawXMLExporter:
    """
    write raw xml into a file
    """

    def open_spider(self, spider):
        self.base_loc = spider.locs.data
        self.soups = {}

    def close_spider(self, spider):
        # write the soup
        for name, soup in self.soups.items():
            soup_file = self.soup_file(name)
            soup_file.write_text(soup.prettify())

    def process_item(self, item, spider):
        if not all(x in item for x in ["source_url", "data"]):
            logging.info("Not XML exporting item: %s", item)
            return item

        soup = self.maybe_create_soup(item['source_url'])

        # add to the soup
        match item['data']:
            case str() as text:
                xml_data                   = BeautifulSoup(text, features="lxml-xml")
            case list() as the_list:
                xml_data                   = BeautifulSoup("\n".join(the_list), features="lxml-xml")
            case _ as unknown:
                logging.warning("Unknown form to save as xml: %s", type(unkown))
                xml_data                   = BeautifulSoup(str(unkown), features="lxml-xml")

        xml_item                   = xml_data.wrap(soup.new_tag("item"))
        xml_item['source_url']     = item['source_url']
        xml_item['parse_date']     = datetime.datetime.now().isoformat()
        xml_item['needs_subsplit'] = item.get('needs_subsplit', False)

        soup.items.append(xml_item)
        return item

    def soup_file(self, netloc:str):
        return (self.base_locs / netloc.replace(".","_")).with_suffix(".xml")

    def maybe_create_soup(self, url:str):
        base_url = urlparse(url).netloc
        if base_url in self.soups:
            return self.soups[base_url]
        soup_file = self.soup_file(base_url)

        if soup_file.exists():
            soup = BeautifulSoup(soup_file.read_text(), features="lxml-xml")
        else:
            soup = BeautifulSoup(features="lxml-xml")
            soup.append(soup.new_tag("items"))
            soup.items['creation_date'] = datetime.datetime.now().isoformat()

        self.soups[base_url] = soup
        return soup

class ItemPipeline:

    # def open_spider(self, spider)
    # def close_spider(self, spider)
    # def from_crawler(cls, crawler)

    def process_item(self, item, spider):
        # must return item, deferred, or raise scrapy.exceptions.DropItem
        return item
