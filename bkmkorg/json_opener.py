#!/Users/jgrey/anaconda/bin/python
import os
import json
import util
import IPython

def open_file(filename):
    x = None
    with open("../data/"+filename, 'r') as f:
        x = f.read()
    return x

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
    
if __name__ == '__main__':
    print('Starting json opener')
    contents = open_file('Firefox.json')
    jsonContents = readJson(contents)
    bookmarks = extractBookmarks(jsonContents)    
    IPython.embed()
    
