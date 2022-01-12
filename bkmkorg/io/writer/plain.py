"""
A Plain Text exporter for bookmarks
"""
import logging as root_logger

logging = root_logger.getLogger(__name__)

from bkmkorg.util.bookmark.collection import Bookmark

def exportBookmarks(data, filename):
    """ Main function. Takes a trie of data and outputs a string """
    #dfs the trie
    #print out the items that are bookmarks
    raise DeprecationWarning("use bkmkorg.utils.bookmark.collection.BookmarkCollection")
