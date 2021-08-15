"""
A Plain Text exporter for bookmarks
"""
import logging as root_logger

logging = root_logger.getLogger(__name__)

from bkmkorg.util.bookmark.data import Bookmark

def exportBookmarks(data, filename):
    """ Main function. Takes a trie of data and outputs a string """
    #dfs the trie
    #print out the items that are bookmarks
    logging.info("Converting data to text")

    frontier = data
    with open(filename, 'w') as f:
        while bool(frontier):
            current = frontier.pop()
            if isinstance(current, Bookmark):
                f.write(current.to_string() + "\n")
            elif isinstance(current, dict):
                frontier += list(current.values())
