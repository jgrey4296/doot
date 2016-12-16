#!/Users/jgrey/anaconda/bin/python
"""
Exports a given trie to Netscape bookmark file format
Main function: exportBookmarks
"""
import logging
import IPython
from bookmark_organiser.bkmkorg.util import bookmarkTuple

groupCount = 0
listCount = 0
entryCount = 0


def header():
    s = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
    <HTML>
    <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
    <Title>Bookmarks</Title>
    <H1>Bookmarks</H1>"""
    return s

def footer():
    return "</HTML>"


#assumes bkmkTuple(title,uri,tags)
def bookmarkToItem(bkmkTuple):
    logging.debug("Exporting link: {}".format(bkmkTuple.url))
    #add the link:
    tags = 'TAGS="{}"'.format(",".join(bkmkTuple.tags))
    item = '<DT><A HREF="{}" {}>{}</A>'.format(bkmkTuple.url,tags, bkmkTuple.name)
    return item

def bookmarksToNetscapeString(data):
    try:
        strings = [convertData(x) for x in data]
        wrapped = "\n".join(strings)
        return wrapped
    except AttributeError as e:
        IPython.embed()


def groupToNetscapeString(name, data):
    group = "<DT><H3 FOLDED> {} </H3> \n\t <DL><p> \n\t\t {} \n\t </DL><p>\n".format(name,convertData(data))
    return group

def convertData(data):
    global groupCount, listCount, entryCount
    if isinstance(data,dict):
        groupCount += 1
        keys = sorted([x for x in data.keys()])
        subGroups = [groupToNetscapeString(x,data[x]) for x in keys if isinstance(data[x],dict) and x != '__path']
        items = [bookmarkToItem(data[x]) for x in keys if isinstance(data[x],bookmarkTuple) and x != '__path']
        combined = subGroups + items
        return '\n'.join(combined)
    else:
        raise Exception('unrecognised conversion type')
    
def exportBookmarks(data):
    """ Main method, returns a complete bookmark string to write to a file """
    formattedString = "{} {} {}".format(header(),convertData(data),footer())
    logging.info("Finished converted bookmarks: {} groups | {} lists | {} entries".format(groupCount,listCount,entryCount))
    return formattedString
