#!/Users/jgrey/anaconda/bin/python
import os
from bs4 import BeautifulSoup
from bookmark_organiser.bkmkorg.json_opener import open_file
from bookmark_organiser.bkmkorg.util import open_file
import logging

def getLinks(aSoup):
    tags = aSoup.find_all('a')
    tupleList = [tuple([x.string,x.get('href')]) for x in tags]
    return tupleList

def open_and_extract_bookmarks(filename):
    logging.info('Starting html opener for: {}'.format(filename))
    rawHtml = open_file(filename)
    soup = BeautifulSoup(rawHtml,'html.parser')
    tupleList = getLinks(soup)
    logging.info("Found {} links".format(len(tupleList)))
    return tupleList


if __name__ == '__main__':
    bookmarks = open_and_extract_bookmarks('Safari.html')
    import IPython
    IPython.embed()
