#!/Users/jgrey/anaconda/bin/python

def writeToFile(data):
    with open('../cleanedBookmarks.html','w') as f:
        f.write(data)

def header():
    s = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
    <Title>Bookmarks</Title>
    <H1>Bookmarks</H1>"""
    return s

def footer():
    return "<\DL>"

#assumes [title,uri]
def bookmarkToItem(bkmk):
    #add the link:
    item = '<DT><A HREF="' + bkmk[1] + '"'
    if len(bkmk) == 3:
        #if tagged, add those:
        tags = bkmk[2]
        item = item + 'TAGS="' + " ".join(tags) + '"'
    #add the title:
    item = item + ">" + bkmk[0] + "</A>"    
    return item

def bookmarksToNetscapeString(data):
    strings = [convertData(x) for x in data]
    wrapped = "\n".join(strings)
    return wrapped

def groupToNetscapeString(name, data):
    group = '<DT><H3 FOLDED>' + name +"</H3><DL><p>"
    group = group + convertData(data)
    group = group + "</DL><p>"
    return group

def convertData(data):
    if type(data) == tuple:
        return bookmarkToItem(data)
    elif type(data) == list:
        return bookmarksToNetscapeString(data)
    elif type(data) == dict:
        subGroups = [groupToNetscapeString(x[0],x[1]) for x in data.items()]
        return '\n'.join(subGroups)
    else:
        print('unrecognised data type')
    
def exportBookmarks(data):
    formattedString = header() + "<DL>" + convertData(data) + footer()
    writeToFile(formattedString)
