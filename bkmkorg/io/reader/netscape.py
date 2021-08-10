"""
Utility to open and parse a netscape bookmark file
https://docs.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/aa753582(v=vs.85)
"""
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

import logging
import os
from collections import namedtuple
from bs4 import BeautifulSoup


from bkmkorg.utils.bookmark.data import bookmarkTuple


def getLinks(aSoup) -> List[bookmarkTuple]:
    bkmks = aSoup.find_all('a')
    tupleList = []
    for x in bkmks:
        tagString = x.get('tags')
        if tagString is not None:
            indTags = tagString.split(',')
        else:
            indTags = []
        tagSet = set(indTags)
        newBkmk = bookmarkTuple(x.get_text(),x.get('href'),tagSet)
        tupleList.append(newBkmk)

    return tupleList

def open_and_extract_bookmarks(filename) -> List[bookmarkTuple]:
    """
    The Main Utility. Takes the path to a filename, returns a list of bookmark tuples
    """
    logging.info('Starting html opener for: {}'.format(filename))
    with open(filename, 'rb') as f:
        rawHtml = f.read().decode("utf-8","ignore")

    soup = BeautifulSoup(rawHtml,'html.parser')
    tupleList = getLinks(soup)
    logging.info("Found {} links".format(len(tupleList)))
    return tupleList


