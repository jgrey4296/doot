#!/Users/jgrey/anaconda/bin/python
import os
from bs4 import BeautifulSoup
from json_opener import open_file
import util

def getLinks(aSoup):
    tags = aSoup.find_all('a')
    tupleList = [tuple([x.string,x.get('href')]) for x in tags]
    return tupleList

def open_and_extract_bookmarks(filename):
    print('Starting html opener')
    rawHtml = open_file(filename)
    soup = BeautifulSoup(rawHtml,'html.parser')
    tupleList = getLinks(soup)
    return tupleList


if __name__ == '__main__':
    bookmarks = open_and_extract_bookmarks('Safari.html')
    import IPython
    IPython.embed()
