#!/Users/jgrey/anaconda/bin/python

import json_opener
import re

slashSplit = re.compile(r'/+')


def filterBadLinks(data):
    return [x for x in data if '//' in x[1]]


#expects [(title,uri)]
def create_trie(data):
    trie = {}
    for x in data:
        insert_trie(trie,x)
    return trie

#side effect: update the passed in trie
def insert_trie(trie,pair):
    uri_list = slice_uri(pair[1])
    if uri_list is None:
        print('skipping')
        return

    currentChild = trie

    for x in uri_list:
        if x not in currentChild:
            currentChild[x] = {}
            
        currentChild = currentChild[x]

    currentChild['__leaf'] = pair[0]
    
    
#split up a uri by its /'s:
#returns [string]
def slice_uri(uri):
    start = uri[0:6]
    #slice off the beginning 
    if start == 'chrome':
        print('found a chrome extension, skipping')
        return None
    elif start == 'file:/':
        rest = uri[7:]
        return ['file://']+slashSplit.split(rest)
    elif start == 'ftp://':
        rest = uri[6:]
        return [start]+slashSplit.split(rest)
    elif start == 'http:/':
        rest = uri[7:]
        return ['http://']+slashSplit.split(rest)
    elif start == 'https:':
        rest = uri[8:]
        return ['https://']+slashSplit.split(rest)
    elif start == 'javasc':
        print('found a javascript bookmark')
        return None
    else:
        print('found an unrecognised bookmark type:')
        print(uri)
        return None


if __name__ == '__main__':
    print('starting on simplification')
    bookmarks = json_opener.open_and_extract_bookmarks('Firefox.json')
    filtered = filterBadLinks(bookmarks)
    trie = create_trie(filtered)
    
    import IPython
    IPython.embed()
