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


from bkmkorg.utils.bookmark.data import Bookmark


def getLinks(aSoup) -> List[Bookmark]:
    bkmks = aSoup.find_all('a')
    bkmkList = []
    for x in bkmks:
        tagString = x.get('tags')
        if tagString is not None:
            indTags = tagString.split(',')
        else:
            indTags = []
        tagSet = set(indTags)
        newBkmk = Bookmark(x.get('href'),tagSet, name=x.get_text())
        bkmkList.append(newBkmk)

    return bkmkList

def open_and_extract_bookmarks(filename) -> List[Bookmark]:
    """
    The Main Utility. Takes the path to a filename, returns a list of bookmarks
    """
    logging.info('Starting html opener for: {}'.format(filename))
    with open(filename, 'rb') as f:
        rawHtml = f.read().decode("utf-8","ignore")

    soup = BeautifulSoup(rawHtml,'html.parser')
    bkmkList = getLinks(soup)
    logging.info("Found {} links".format(len(bkmkList)))
    return bkmkList
