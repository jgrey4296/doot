from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
import re

import logging as root_logger
logging = root_logger.getLogger(__name__)

from bkmkorg.utils.bookmark.data import Bookmark

ext = ".bookmarks"

def load_plain_file(path, ext=ext):
    """ Load a plain bookmarks file where each line is:
    url : tag,tag,...

    Expects an expanded path
    Returns: List[]
    """
    logging.info(f"Loading plain bookmarks: {path}")
    assert(exists(path))
    assert(splitext(path)[1] == ext)
    bookmarks = []
    # open file
    lines = []
    with open(path, 'r') as f:
        lines = f.readlines()

    logging.info(f"Found {len(lines)} lines")
    for line in lines:
        bookmarks.append(Bookmark.build(line))

    return bookmarks
