"""
Exports a given trie to Netscape bookmark file format
Main function: exportBookmarks
"""
##-- imports
from __future__ import annotations

import logging

from bkmkorg.bookmarks.collection import Bookmark
##-- end imports

groupCount = 0
listCount  = 0
entryCount = 0


def _header():
    """ Creates the Header for the entire bookmark file """
    s = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
    <HTML>
    <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
    <Title>Bookmarks</Title>
    <H1>Bookmarks</H1>
    """
    return s

def _footer():
    """ Finishs the bookmark file """
    return "\n</HTML>"


def _bookmarkToItem(bkmk):
    """ Converts a single bookmark to html """
    assert(isinstance(bkmk, Bookmark))
    logging.debug("Exporting link: %s", bkmk.url)
    #add the link:
    tags = 'TAGS="{}"'.format(",".join(sorted(bkmk.tags)))
    item = '<DT><A HREF="{}" {}>{}</A>'.format(bkmk.url,tags, bkmk.name.replace('\n',''))
    return item

def _bookmarksToNetscapeString(data):
    strings = [_convertData(x) for x in data]
    wrapped = "\n".join(strings)
    return wrapped


def _groupToNetscapeString(name, data):
    group = "<DT><H3 FOLDED> {} </H3> \n\t <DL><p> \n\t\t {} \n\t </DL><p>\n".format(name,_convertData(data))
    return group

def _convertData(data):
    global groupCount, listCount, entryCount
    match data:
        case dict():
            groupCount  += 1
            keys         = sorted([x for x in data.keys()])
            subGroups    = [_groupToNetscapeString(x,data[x]) for x in keys if isinstance(data[x],dict) and x != '__path']
            items        = [_bookmarkToItem(data[x]) for x in keys if isinstance(data[x], Bookmark) and x != '__path']
            combined     = subGroups + items
            return '\n'.join(sorted(combined))
        case list():
            entryCount = len(data)
            return "\n".join(sorted([_bookmarkToItem(x) for x in data]))
        case _:
            raise Exception('Unrecognised conversion type: %s', type(data))

def exportBookmarks(data:list|dict, target:pl.Path):
    """ Main function, returns a complete bookmark string to write to a file """
    formattedString = "{} {} {}".format(_header(),
                                        _convertData(data),
                                        _footer())
    logging.info("Finished converted bookmarks: %s groups | %s lists | %s entries", groupCount,listCount,entryCount)
    target.write_text(formatted_string)
