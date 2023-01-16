#!/usr/bin/env python3
"""
a collection of different transformers for bibtex entries
from their raw load form, to various nicer formats.
eg: split out authors, split tags, force to unicode...
"""
##-- imports
from __future__ import annotations

import datetime
import logging as root_logger
import re

import bibtexparser as b
from bibtexparser import customization as c
##-- end imports

logging = root_logger.getLogger(__name__)

NEWLINE_RE        = re.compile(r"\n+\s*")

def nop(record):
    return record

def to_unicode(record):
    record = b.customization.convert_to_unicode(record)
    record = {k:NEWLINE_RE.sub(" ", v) for k,v in record.items()}
    return record

def basic_clean(record):
    """
    basic transforms from bibtexparser
    """
    record = c.type(record)
    record = c.author(record)
    record = c.editor(record)
    record = c.journal(record)
    record = c.keyword(record)
    record = c.link(record)
    record = c.doi(record)

    return record

def tag_split(record):
    tags = set()

    if 'tags' in record and isinstance(record['tags'], str):
        tags.update([i.strip() for i in re.split(r',|;', record["tags"].replace('\n', ''))])
    if "keywords" in record and isinstance(record['keywords'], str):
        tags.update([i.strip() for i in re.split(r',|;', record["keywords"].replace('\n', ''))])
        del record['keywords']
    if "mendeley-tags" in record and isinstance(record['mendeley-tags'], str):
        tags.update([i.strip() for i in re.split(r',|;', record["mendeley-tags"].replace('\n', ''))])
        del record['mendeley-tags']

    record['__tags'] = tags
    return record

def split_names(record):
    """
    split tags, author and editors, as unicode
    """
    def separate_names(text):
        return c.getnames([i.strip() for i in re.split(r"\ and\ ", text.replace('\n', ' '), flags=re.IGNORECASE)])

    try:
        match record:
            case { "author": author }:
                separated = separate_names(author)
                record['__authors'] = [c.splitname(x, False) for x in separated]
            case { "editor" : editor }:
                separated = separate_names(editor)
                record['__editors'] = [c.splitname(x, False) for x in separated]
            case _:
                raise Exception("No author or editor")
    except Exception as err:
        logging.warning("Error processing %s : %s", record['ID'], err)

    return record

def year_parse(record):
    """
    parse the year into a datetime
    """
    if 'year' not in record:
        year_temp = "2020"
    else:
        year_temp = record['year']

    if "/" in year_temp:
        year_temp = year_temp.split("/")[0]

    year = datetime.datetime.strptime(year_temp, "%Y")
    record['__year'] = year

    return record


