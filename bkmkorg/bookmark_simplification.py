#!/Users/jgrey/anaconda/bin/python
"""
A File to process tuple lists of bookmarks into a trie that simplifies into similar domains.

"""
import bookmark_organiser.bkmkorg.json_opener
import bookmark_organiser.bkmkorg.netscape_bookmark_exporter as ns_b_e
from bookmark_organiser.bkmkorg.util import bookmarkTuple
import re
import logging

#REGEXS:
slashSplit = re.compile(r'/+')
#for skipping:
filereg = re.compile(r'file:/(?:/?)')
jsreg = re.compile(r'^javascript:')
chromereg = re.compile(r'^chrome')
#for processing:
ftpreg = re.compile(r'(ftp:/(?:/)?)(.*)')
httpreg = re.compile(r'(http(?:s)?:/(?:/)?)(.*)')

entryCount = 0
overwriteCount = 0


def filterBadLinks(data):
    """
    Filters out links that begin with /. ie: /file:blah
    """
    return [x for x in data if '//' in x[1]]


def create_trie(data):
    """ Utility method to create a trie from data """
    #expects [(title,uri)]
    trie = {}
    for x in data:
        insert_trie(trie,x)
    return trie

def insert_trie(trie,bkmkTuple):
    """
    Modify a trie, inserting a bookmark tuple in, furthest down the trie 
    based on url components
    """
    #side effect: update the passed in trie
    #takes a tuple of (name,link)
    if bkmkTuple.name is None:
        logging.debug("No Name: {}".format(bkmkTuple))
        bkmkTuple = bookmarkTuple("Unknown Name",bkmkTuple.url,bkmkTuple.tags)
    
    uri_list = slice_uri(bkmkTuple.url)
    if uri_list is None:
        logging.debug("Skipping: {}".format(bkmkTuple))
        return False

    currentChild = trie

    for x in uri_list:
        if x not in currentChild:
            currentChild[x] = {}
        currentChild = currentChild[x]

    if '__leaf' in currentChild and not currentChild['__leaf'].url == bkmkTuple.url:
        logging.debug('Overwriting:')
        logging.debug(currentChild['__leaf'])
        logging.debug(bkmkTuple)
        global overwriteCount
        overwriteCount += 1
    else:
        global entryCount
        currentChild['__leaf'] = bkmkTuple
        entryCount += 1

    return True
    
#split up a uri by its /'s:
#returns [string]
def slice_uri(uri):
    """ Utility method to handle different url types 
    get the type of bookmark, if ftp or http(s) -> split and return
    """
    if chromereg.match(uri) or filereg.match(uri) or jsreg.match(uri):
        logging.debug('found a chromeex/file/js, skipping')
        return None
    elif ftpreg.match(uri):
        group = ftpreg.findall(uri)
        if len(group) < 1:
            raise Exception("ftpreg matched but didnt group on: {}".format(uri))
        return [group[0][0]] + slashSplit.split(group[0][1])
    elif httpreg.match(uri):
        group = httpreg.findall(uri)
        if len(group) < 1:
            raise Exception("httpreg matched but didnt group on: {}".format(uri))
        return [group[0][0]] + slashSplit.split(group[0][1])
    else:
        logging.debug("Found an unrecognised bookmark type: {}".format(uri))
        return None

def groupTrie(trie):
    """ top level grouping """
    outputData = {}
    currentList = list(trie.items())
    while len(currentList) > 0:
        name,data = currentList.pop()
        if isinstance(data,bookmarkTuple):
            outputData[name] = [data]
        elif isinstance(data,dict):
            outputData[name] = subTrie(data)
        else:
            raise Exception("Unexpected type in top level grouping")
    return outputData

def subTrie(trie):
    """ sub-level trie grouping """
    outputData = []
    if isinstance(trie,bookmarkTuple):
        outputData.append(trie)
    elif isinstance(trie,list):
        for x in trie:
            outputData += subTrie(x)
    elif isinstance(trie,dict):
        for x in trie.values():
            outputData += subTrie(x)
    return outputData


def returnCounts():
    global entryCount,overwriteCount
    vals = (entryCount,overwriteCount)
    entryCount = 0
    overwriteCount = 0
    return vals

