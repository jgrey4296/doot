#!/Users/jgrey/anaconda/bin/python

import json_opener
import html_opener
import netscape_bookmark_exporter as ns_b_e
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

    if '__leaf' in currentChild and not currentChild['__leaf'][1] == pair[1]:
        print('overwriting:')
        print(currentChild['__leaf'])
        print(pair)
    else:
        currentChild['__leaf'] = pair
    
    
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

def flattenTrie(trie):
    outputData = []
    toProcess = list(trie.items())
    while len(toProcess) > 0:
        current = toProcess.pop()
        if current[0] == '__leaf' and type(current[1]) == tuple:
            outputData.append(current[1])
        elif type(current[1]) == dict:
            toProcess = toProcess + list(current[1].items())
        else:
            raise Exception('unknown trie component')
    return outputData

def groupTrie(trie):
    outputData = {}
    for tName,data in trie.items():
        for dName,instances in data.items():
            outputData[dName] = flattenTrie(instances)
    return outputData


if __name__ == '__main__':
    print('starting on simplification')
    json_bookmarks = json_opener.open_and_extract_bookmarks('Firefox.json')
    #html_bookmarks = html_opener.open_and_extract_bookmarks('Safari.html')
    bookmarks = json_bookmarks
    filtered = filterBadLinks(bookmarks)
    trie = create_trie(filtered)
    #convert the trie back to individual bookmarks:
    #flattened = flattenTrie(trie)
    #ns_b_e.exportBookmarks(flattened)
    grouped = groupTrie(trie)
    ns_b_e.exportBookmarks(grouped)
    import IPython
    IPython.embed()
