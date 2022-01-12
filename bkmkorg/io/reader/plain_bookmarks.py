import logging as root_logger
logging = root_logger.getLogger(__name__)

def load_plain_file(path, ext=None):
    """ Load a plain bookmarks file where each line is:
    url : tag,tag,...

    Expects an expanded path
    Returns: List[]
    """
    raise DeprecationWarning("Use bkmkorg.utils.bookmark.collection.BookmarkCollection")
