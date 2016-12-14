#!/Users/jgrey/anaconda/bin/python
import os
from bs4 import BeautifulSoup
from collections import namedtuple
from bookmark_organiser.bkmkorg.util import open_file,bookmarkTuple
import logging

def getLinks(aSoup):
    tags = aSoup.find_all('a')
    tupleList = [bookmarkTuple(x.string,x.get('href'),x.get('tags') or []) for x in tags]
    return tupleList

def open_and_extract_bookmarks(filename):
    logging.info('Starting html opener for: {}'.format(filename))
    rawHtml = open_file(filename)
    soup = BeautifulSoup(rawHtml,'html.parser')
    tupleList = getLinks(soup)
    logging.info("Found {} links".format(len(tupleList)))
    return tupleList


