"""
Exports a given trie to Netscape bookmark file format
Main function: exportBookmarks
"""
##-- imports
from __future__ import annotations

import logging

##-- end imports

from bs4 import BeautifulSoup
from doot.utils.formats.bookmarks import Bookmark, BookmarkCollection

class NetscapeLoader:

    @staticmethod
    def read_netscape(path:pl.Path):
        logging.info('Starting html opener for: %s', path)
        with open(path, 'rb') as f:
            rawHtml = f.read().decode("utf-8","ignore")

        soup     = BeautifulSoup(rawHtml,'html.parser')
        bkmkList = NetscapeLoader._getLinks(soup)
        logging.info("Found %s links", len(bkmkList))
        return BookmarkCollection(bkmkList)

    @staticmethod
    def _getLinks(aSoup) -> List[Bookmark]:
        bkmks = aSoup.find_all('a')
        bkmkList = []
        for x in bkmks:
            tagString = x.get('tags')
            if tagString is not None:
                indTags = tagString.split(',')
            else:
                indTags = []
            tagSet = set(indTags)
            newBkmk = Bookmark(x.get('href'),tagSet, name=x.get_text())
            bkmkList.append(newBkmk)

        return bkmkList

class NetscapeWriter:

    groupCount = 0
    listCount  = 0
    entryCount = 0
    _header = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
    <HTML>
    <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
    <Title>Bookmarks</Title>
    <H1>Bookmarks</H1>
    """
    _footer = "\n</HTML>"
    _group  = "<DT><H3 FOLDED> {} </H3> \n\t <DL><p> \n\t\t {} \n\t </DL><p>\n"
    _tags   = 'TAGS="{}"'
    _item   = '<DT><A HREF="{}" {}>{}</A>'

    @staticmethod
    def exportBookmarks(data:list|dict, target:pl.Path):
        """ Main function, returns a complete bookmark string to write to a file """
        writer = NetscapeWriter()

        result = []
        result.append(writer.header())
        results += _convertData(data)
        result.append(footer())
        logging.info("Finished converted bookmarks: %s groups | %s lists | %s entries", groupCount,listCount,entryCount)
        target.write_text(formatted_string)

    def header(self):
        """ Creates the Header for the entire bookmark file """
        return self.header

    def footer(self):
        """ Finishs the bookmark file """
        return self._footer

    def convertData(self, data) -> list[str]:
        results = []
        match data:
            case dict():
                self.groupCount  += 1
                keys         = sorted([x for x in data.keys()])
                results += [self.groupToNetscapeString(x,data[x]) for x in keys if isinstance(data[x],dict) and x != '__path']
                results += [self.bookmarkToItem(data[x]) for x in keys if isinstance(data[x], Bookmark) and x != '__path']
            case list():
                entryCount = len(data)
                results += [self.bookmarkToItem(x) for x in data]
            case _:
                raise Exception('Unrecognised conversion type: %s', type(data))

        return "\n".join(sorted(results))

    def groupToNetscapeString(self, name, data):
        return self._group.format(name,self.convertData(data))

    def bookmarkToItem(self, bkmk):
        """ Converts a single bookmark to html """
        assert(isinstance(bkmk, Bookmark))
        logging.debug("Exporting link: %s", bkmk.url)
        #add the link:
        tags = self._tags.format(",".join(sorted(bkmk.tags)))
        item = self._item.format(bkmk.url,tags, bkmk.name.replace('\n',''))
        return item
