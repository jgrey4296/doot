"""
Utility to open and parse a netscape bookmark file
"""

import os
from bs4 import BeautifulSoup
from collections import namedtuple
from bookmark_organiser.bkmkorg.util import open_file,bookmarkTuple
import logging

def getLinks(aSoup):
    bkmks = aSoup.find_all('a')
    tupleList = []
    for x in bkmks:
        tagString = x.get('tags')
        if tagString is not None:
            indTags = tagString.split(',')
        else:
            indTags = []
        tagSet = set(indTags)
        newBkmk = bookmarkTuple(x.string,x.get('href'),tagSet)
        tupleList.append(newBkmk)

    return tupleList

def open_and_extract_bookmarks(filename):
    """
    The Main Utility. Takes the path to a filename, returns a list of bookmark tuples
    """
    logging.info('Starting html opener for: {}'.format(filename))
    rawHtml = open_file(filename)
    soup = BeautifulSoup(rawHtml,'html.parser')
    tupleList = getLinks(soup)
    logging.info("Found {} links".format(len(tupleList)))
    return tupleList


