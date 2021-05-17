"""
A Plain Text exporter for bookmarks
"""
import logging as root_logger
from bkmkorg.utils.bookmark.bookmark_data import bookmarkTuple

logging = root_logger.getLogger(__name__)

def tuple_to_str(bkmk_tuple):
    return "{} ||| :{}: ||| {}".format(bkmk_tuple.name,
                                       ":".join(bkmk_tuple.tags),
                                       bkmk_tuple.url)


def exportBookmarks(data, filename):
    """ Main function. Takes a trie of data and outputs a string """
    #dfs the trie
    #print out the items that are bookmark tuples
    logging.info("Converting data to text")

    frontier = data
    with open(filename, 'w') as f:
        while bool(frontier):
            current = frontier.pop()
            if isinstance(current, bookmarkTuple):
                theString = tuple_to_str(current) + "\n"
                f.write(theString)
            elif isinstance(current, dict):
                frontier += list(current.values())
