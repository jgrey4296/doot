#!/usr/bin/env python3
import logging as root_logger
import re
import datetime

logging = root_logger.getLogger(__name__)

import bibtexparser as b
from bibtexparser import customization as c


def nop(record):
    # record = c.type(record)
    # record = c.author(record)
    # record = c.editor(record)
    # record = c.journal(record)
    # record = c.keyword(record)
    # record = c.link(record)
    # record = c.doi(record)
    # record['tags'] = [i.strip() for i in re.split(',|;', record["tags"].replace("\n",""))]
    # record['p_authors'] = []
    # if 'author' in record:
    #     record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record



def clean_full(record):
    record = c.type(record)
    record = c.author(record)
    record = c.editor(record)
    record = c.journal(record)
    record = c.keyword(record)
    record = c.link(record)
    record = c.doi(record)
    tags = set()

    if 'tags' in record:
        tags.update([i.strip() for i in re.split(',|;', record["tags"].replace('\n', ''))])
    if "keywords" in record:
        tags.update([i.strip() for i in re.split(',|;', record["keywords"].replace('\n', ''))])
    if "mendeley-tags" in record:
        tags.update([i.strip() for i in re.split(',|;', record["mendeley-tags"].replace('\n', ''))])

    record['tags']      = tags
    record['p_authors'] = []

    if 'author' in record:
        record['p_authors'] += [x.split(' and ') for x in record['author']]

    if 'editor' in record:
        record['p_authors'] += [c.splitname(x, False) for x in record['editor']]

    return record


def clean(record):
    # record = c.type(record)
    # record = c.author(record)
    # record = c.editor(record)
    # record = c.journal(record)
    # record = c.keyword(record)
    # record = c.link(record)
    # record = c.doi(record)
    tags = set()

    if 'tags' in record:
        tags.update([i.strip() for i in re.split(',|;', record["tags"].replace('\n', ''))])
    if "keywords" in record:
        tags.update([i.strip() for i in re.split(',|;', record["keywords"].replace('\n', ''))])
    if "mendeley-tags" in record:
        tags.update([i.strip() for i in re.split(',|;', record["mendeley-tags"].replace('\n', ''))])

    record['tags'] = tags
    # record['p_authors'] = []
    # if 'author' in record:
    #     record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record

def tags(record):
    record = b.customization.convert_to_unicode(record)
    record = c.author(record)
    record = c.editor(record)
    tags = set()

    if 'tags' in record:
        tags.update([i.strip() for i in re.split(',|;', record["tags"].replace('\n', ''))])

    record['tags'] = tags
    record['p_authors'] = []
    logging.debug(f"Handling: {record['ID']}")
    if 'author' in record:
        try:
            record['p_authors'] = [c.splitname(x, False) for x in record['author']]
        except Exception as err:
            breakpoint()
    if 'editor' in record:
        record['p_authors'] = [c.splitname(x, False) for x in record['editor']]

    return record

def tag_summary(record):
    if 'year' not in record:
        year_temp = "2020"
    else:
        year_temp = record['year']
    if "/" in year_temp:
        year_temp = year_temp.split("/")[0]

    year = datetime.datetime.strptime(year_temp, "%Y")
    tags = []
    if 'tags' in record:
        tags = [x.strip() for x in record['tags'].split(",")]

    record['year'] = year
    record['tags'] = tags

    return record

def author_extract(record):
    record = c.author(record)
    record = c.editor(record)
    return record


def year_parse(record):
    if 'year' not in record:
        year_temp = "2020"
    else:
        year_temp = record['year']

    if "/" in year_temp:
        year_temp = year_temp.split("/")[0]

    year = datetime.datetime.strptime(year_temp, "%Y")
    tags = []
    if 'tags' in record:
        tags = [x.strip() for x in record['tags'].split(",")]

    record['year'] = year
    record['tags'] = tags

    return record
