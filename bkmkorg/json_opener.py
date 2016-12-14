#!/Users/jgrey/anaconda/bin/python
import os
import json
import bookmark_organiser.bkmkorg.util
from bookmark_organiser.bkmkorg.util import open_file

def readJson(text):
    return json.loads(text)

def extractBookmarks(jsonContents):
    #set of found items by guid:
    explored = set()
    #a list of tuples (title,uri) to populate
    bookmarks = []
    #the list of queued nodes to search
    queue = [jsonContents]
    #start searching:
    while(len(queue) > 0):
        head, *queue = queue
        if head['guid'] not in explored:
            #add to set
            explored.add(head['guid'])
            if 'uri' in head:
                #is a bookmark, store as a tuple:
                try:
                    if 'title' in head:
                        bookmarks.append(tuple([head['title'],head['uri']]))
                    else:
                        bookmarks.append(tuple([head['uri'],head['uri']]))
                except KeyError as e:
                    print(e)
                    print(head['guid'])
            if 'children' in head:
                #is a folder:
                queue = queue + head['children']
    #loop finished, bookmarks now contains all uri's
    return bookmarks

def open_and_extract_bookmarks(filename):
    print('Starting json opener')
    contents = open_file(filename)
    jsonContents = readJson(contents)
    bookmarks = extractBookmarks(jsonContents)
    return bookmarks
    
if __name__ == '__main__':
    bookmarks = open_and_extract_bookmarks('Firefox.json')
    import IPython
    IPython.embed()
    
