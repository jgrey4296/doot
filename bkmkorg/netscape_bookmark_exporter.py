#!/Users/jgrey/anaconda/bin/python
"""
Exports a given trie to Netscape bookmark file format
Main function: exportBookmarks
"""
import logging

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


#assumes [title,uri]
def bookmarkToItem(bkmk):
    logging.debug("Exporting link: {}".format(bkmk[0]))
    #add the link:
    if len(bkmk) == 3:
        tags = 'TAGS="{}"'.format(" ".join(bkmk[2]))
    else:
        tags = ""
    item = '<DT><A HREF="{}" {}>{}</A>'.format(bkmk[1],tags, bkmk[0])
    return item

def bookmarksToNetscapeString(data):
    strings = [convertData(x) for x in sorted(data)]
    wrapped = "\n".join(strings)
    return wrapped

def groupToNetscapeString(name, data):
    group = "<DT><H3 FOLDED> {} </H3> \n\t <DL><p> \n\t\t {} \n\t </DL><p>\n".format(name,convertData(data))
    return group

def convertData(data):
    global groupCount, listCount, entryCount
    if type(data) == tuple:
        entryCount += 1
        return bookmarkToItem(data)
    elif type(data) == list:
        listCount += 1
        return bookmarksToNetscapeString(data)
    elif type(data) == dict:
        groupCount += 1
        items = sorted([x for x in data.items()])
        subGroups = [groupToNetscapeString(x[0],x[1]) for x in items]
        return '\n'.join(subGroups)
    else:
        logging.debug('unrecognised data type')
    
def exportBookmarks(data):
    """ Main method, returns a complete bookmark string to write to a file """
    formattedString = "{} {} {}".format(header(),convertData(data),footer())
    logging.info("Finished converted bookmarks: {} groups | {} lists | {} entries".format(groupCount,listCount,entryCount))
    return formattedString
