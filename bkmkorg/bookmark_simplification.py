#!/Users/jgrey/anaconda/bin/python
"""
A File to process tuple lists of bookmarks into a trie that simplifies into similar domains.

"""
import bookmark_organiser.bkmkorg.json_opener
import bookmark_organiser.bkmkorg.netscape_bookmark_exporter as ns_b_e
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

def insert_trie(trie,pair):
    """
    Modify a trie, inserting a bookmark pair in, furthest down the trie 
    based on url components
    """
    #side effect: update the passed in trie
    #takes a tuple of (name,link)
    if pair[0] is None:
        logging.debug("No Name: {}".format(pair))
        pair = tuple(["Unknown Name",pair[1]])
    
    uri_list = slice_uri(pair[1])
    if uri_list is None:
        logging.debug("Skipping: {}".format(pair))
        return

    currentChild = trie

    for x in uri_list:
        if x not in currentChild:
            currentChild[x] = {}
        currentChild = currentChild[x]

    if '__leaf' in currentChild and not currentChild['__leaf'][1] == pair[1]:
        logging.debug('Overwriting:')
        logging.debug(currentChild['__leaf'])
        logging.debug(pair)
        global overwriteCount
        overwriteCount += 1
    else:
        global entryCount
        currentChild['__leaf'] = pair
        entryCount += 1
    
    
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

def flattenTrie(trie):
    """ Converts a sub-trie to its minimal form,
    ie: any sequence of branches that only have 1 leaf are collapsed together
    """
    outputData = []
    toProcess = list(trie.items())
    while len(toProcess) > 0:
        current = toProcess.pop()
        if current[0] == '__leaf' and isinstance(current[1],tuple):
            outputData.append(current[1])
        elif isinstance(current[1],dict):
            toProcess = toProcess + list(current[1].items())
        else:
            raise Exception('unknown trie component')
    return outputData

def groupTrie(trie):
    """
    Takes the root of a trie and flattens the entire thing
    """
    outputData = {}
    for tName,data in trie.items():
        for dName,instances in data.items():
            outputData[dName] = flattenTrie(instances)
    return outputData

def returnCounts():
    global entryCount,overwriteCount
    vals = (entryCount,overwriteCount)
    entryCount = 0
    overwriteCount = 0
    return vals


if __name__ == '__main__':
    logging.debug('starting on simplification')
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
