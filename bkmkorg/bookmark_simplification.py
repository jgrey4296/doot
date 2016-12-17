#!/Users/jgrey/anaconda/bin/python
"""
A File to process tuple lists of bookmarks into a trie that simplifies into similar domains.

"""
import bookmark_organiser.bkmkorg.netscape_bookmark_exporter as ns_b_e
from bookmark_organiser.bkmkorg.util import bookmarkTuple
import re
import logging
from collections import namedtuple
from bookmark_organiser.verifySites import verifyUrl, TOFIX_TAG, VERIFIED_TAG

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
    #takes a bookmarkTuple
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
        raise Exception("Name and url exist but don't match")
    else:
        global entryCount
        tofix_or_verified_tag_in_bkmk_tags = (TOFIX_TAG in bkmkTuple.tags \
                                              or VERIFIED_TAG in bkmkTuple.tags)
        if not tofix_or_verified_tag_in_bkmk_tags:
            if verifyUrl(bkmkTuple.url):
                logging.debug('Verifed')
                bkmkTuple.tags.add(VERIFIED_TAG)
            else:
                logging.debug('tofix')
                bkmkTuple.tags.add(TOFIX_TAG)


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
    """ dfs the trie, collapsing paths together of only 1 child """
    logging.debug("Grouping the Trie")
    POP = namedtuple('Pop',"name")
    PUSH = namedtuple('Push',"name")
    Entry = namedtuple('Entry',"name dict parent")
    Leaf = namedtuple("Leaf","name bkmk parent")
    
    output = {'__path':''}
    frontier = [Entry("root",trie, output)]
        
    while len(frontier) > 0:
        node = frontier.pop()
        if isinstance(node,POP):
            logging.debug("Popping: {}".format(node.name))
        elif isinstance(node,PUSH):
            logging.debug("Pushing: {}".format(node.name))
        elif isinstance(node,Entry):
            name = node.name
            data = node.dict
            parent = node.parent
            logging.debug("Entry: {}".format(name))
            if isinstance(data,bookmarkTuple):
                if name != "__leaf":
                    raise Exception("Unexpected non-leaf bkmkTuple")
                logging.debug("Early Leaf")
                frontier.append(Leaf(data.name,data,parent))                
            elif len(data.keys()) == 1:
                logging.debug("Only one child")
                subName,subData = list(data.items())[0]
                if subName == "__leaf":
                    newNode = {'__path':"{}/{}".format(parent['__path'],name)}
                    parent[name] = newNode
                    leafName = subData.name
                    logging.debug("Adding Leaf name: {}".format(leafName))
                    frontier.append(Leaf(leafName,subData,newNode))
                else:
                    combinedName = "{}/{}".format(name,subName)
                    logging.debug("Combined name: {}".format(combinedName))
                    newEntry = Entry(combinedName,subData,parent)
                    frontier.append(newEntry)
            else:
                logging.debug("Multiple children")
                logging.debug("New Node: {} --> {}".format(parent['__path'], name))
                newNode = {'__path':"{}/{}".format(parent['__path'],name)}
                parent[name] = newNode
                children = [POP(name)] + [Entry(x,y,newNode) for x,y in data.items()] + [PUSH(name)]
                frontier += children

        if isinstance(node,Leaf):
            name = node.name
            bkmk = node.bkmk
            parent = node.parent
            logging.debug("Leaf: {} --> {}".format(parent['__path'],name))
            logging.debug("Leaf url: {}".format(bkmk.url))
            if name in parent:
                if isinstance(parent[name],list):
                    urls = [x.url for x in parent[name]]
                else:
                    urls = [parent[name].url]
                                               
                if bkmk.url in urls:
                    #already exists, combine the tags
                    existingTuple = parent[name]
                    unionTags = bkmk.tags.union(parent[name].tags)

                    parent[name] = bookmarkTuple(existingTuple.name,
                                                 existingTuple.url,
                                                 unionTags)

                else:
                    logging.warning("Unexpected duplication")
                    IPython.embed()
                    # old = parent[name]
                    # if isinstance(old,list):
                    #         old.append(bkmk)
                    # else:
                    #         parent[name] = [old,bkmk]
            else:
                parent[name] = bkmk

    return output


def returnCounts():
    global entryCount,overwriteCount
    vals = (entryCount,overwriteCount)
    entryCount = 0
    overwriteCount = 0
    return vals

