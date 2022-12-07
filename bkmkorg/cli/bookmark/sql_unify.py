#/usr/bin/env python3
"""
A Direct Firefox sqlite databse -> bookmarks file merger
uses pony
"""
##-- imports
from __future__ import annotations

import abc
import argparse
import configparser
import logging as logmod
import pathlib as pl
import tempfile
from collections import defaultdict
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from importlib.resources import files
from re import Pattern
from shutil import copy
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import pony.orm as pony
from bkmkorg.bookmarks import collection as BC

##-- end imports

##-- logging
DISPLAY_LEVEL = logmod.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
LOG_FORMAT    = "%(asctime)s | %(levelname)8s | %(message)s"
FILE_MODE     = "w"
STREAM_TARGET = stderr # or stdout

logger          = logmod.getLogger(__name__)
console_handler = logmod.StreamHandler(STREAM_TARGET)
file_handler    = logmod.FileHandler(LOG_FILE_NAME, mode=FILE_MODE)

console_handler.setLevel(DISPLAY_LEVEL)
# console_handler.setFormatter(logmod.Formatter(LOG_FORMAT))
file_handler.setLevel(logmod.DEBUG)
# file_handler.setFormatter(logmod.Formatter(LOG_FORMAT))

logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.setLevel(DISPLAY_LEVEL)
logging = logger
##-- end Logging

##-- argparse
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))
parser.add_argument('-t', '--target')#, required=True)
parser.add_argument('-v', '--verbose', action="store_true")
parser.add_argument('-n', '--non-interactive', action="store_true")
##-- end argparse

##-- data
data_path   = files("bkmkorg.__config")
config_file = data_path / "bots.config"
##-- end data

# Database is found at ~/Library/ApplicationSupport/Firefox/Profiles/?/places.sqlite
# tables of interest: moz_bookmarks and moz_places

##-- initiatilization
db = pony.Database()
##-- end initiatilization

##-- ORM
class Bookmark(db.Entity):
    """
    Schema of moz_bookmarks
    type   = 1 if bookmark, 2 if metadata
    parent = 4 if a tag
    fk     = foreign key to moz_place for url

    So a bookmark uses fk to point to the url.
    If the bookmark has tags, each tag is a bookmark entry,
    with no title, same fk as the bookmark,
    parent points to the tag name entry.
    The tag name entry has a title, but no fk
    and it's parent points to entry 4: 'tags'
    """
    _table_                 = "moz_bookmarks"
    type              : int = pony.Required(int)
    fk                : int = pony.Optional(int)
    parent            : int = pony.Required(int)
    position          : int = pony.Required(int)
    title             : str = pony.Optional(str)
    keyword_id        : int = pony.Optional(int)
    folder_type       : str = pony.Optional(str)
    dateAdded         : int = pony.Required(int)
    lastModified      : int = pony.Required(int)
    guid              : str = pony.Required(str)
    syncStatus        : int = pony.Required(int)
    syncChangeCounter : int = pony.Required(int)


class URL(db.Entity):
    """
    a url entry in moz_places.
    url field is the important bit.
    the URL's id is used for the fk of a bookmark
    """
    _table_                 = "moz_places"
    url               : str = pony.Required(str)
    title             : str = pony.Optional(str)
    rev_host          : str = pony.Required(str)
    visit_count       : int = pony.Required(int)
    hidden            : int = pony.Required(int)
    typed             : int = pony.Required(int)
    frecency          : int = pony.Required(int)
    last_visit_date   : int = pony.Optional(int)
    guid              : str = pony.Required(str)
    foreign_count     : int = pony.Required(int)
    url_hash          : int = pony.Required(int)
    description       : str = pony.Optional(str)
    preview_image_url : str = pony.Optional(str)
    origin_id         : int = pony.Required(int)
    site_name         : str = pony.Optional(str)

##-- end ORM

def main():
    args = parser.parse_args()
    if args.target:
        args.target = pl.Path(args.target).expanduser().resolve()
        assert(args.target.exists())

    ##-- debugging
    pony.set_sql_debug(args.verbose)
    ##-- end debugging

    config = configparser.ConfigParser()
    with open(config_file, 'r') as f:
              config.read_file(f)
    firefox : Path = pl.Path(config['BOOKMARK']["firefox"]).expanduser().resolve()
    assert(firefox.exists()), str(firefox)
    dbs = []
    for loc in (firefox / "Profiles").iterdir():
        maybe_db = loc / config['BOOKMARK']['database']
        if maybe_db.exists():
            dbs.append(maybe_db)

    # find the database
    logging.info("Found %s databases", len(dbs))
    logging.info("Using database: %s", str(dbs[0]))

    tag_names = {}
    bookmark_tags = defaultdict(lambda: set())
    collection : BC.BookmarkCollection = BC.BookmarkCollection()

    with tempfile.TemporaryDirectory() as temp_dir:
        ##-- copy database so its not locked
        copy_target = pl.Path(temp_dir) / dbs[0].name
        copy(str(dbs[0]), str(copy_target))
        ##-- end copy database so its not locked

        ##-- bind database and mappings
        db.bind(provider='sqlite', filename=str(copy_target), create_db=False)
        db.generate_mapping(create_tables=False)
        ##-- end bind database and mappings

        ##-- session use
        logging.info("Extracting bookmarks")
        with pony.db_session:
            tag_names = {b.id : b.title for b in pony.select(b for b in Bookmark if b.title is not None and b.fk is None and b.parent == 4)}
            for b in pony.select(b for b in Bookmark if b.title is None and b.fk is not None):
                if b.parent not in tag_names:
                    continue
                bookmark_tags[b.fk].add(tag_names[b.parent])

            query  = pony.select(b for b in Bookmark if b.title is not None and b.fk is not None)
            result = query[:]
            for x in result:
                bkmk : BC.Bookmark = BC.Bookmark(URL[x.fk].url,
                                                bookmark_tags[x.fk],
                                                x.title)
                collection += bkmk
        ##-- end session use

    logging.info("Extracted %s bookmarks from firefox", len(collection))

    if args.target:
        logging.info("Merging into %s", args.target)
        existing      = BC.BookmarkCollection.read(args.target)
        original_amnt = len(existing)
        existing += collection
        existing.merge_duplicates()

        logging.info("Merged to produce: %s(+%s) total bookmarks", len(existing), len(existing) - original_amnt)

        if (not args.non_interactive) and input("Overwrite {}? */n ".format(args.target)) == "n":
            logging.info("Quitting without saving")
            exit()

        with open(args.target, 'w') as f:
            f.write(str(existing))

        logging.info("Data written, finished")

##-- ifmain
if __name__ == '__main__':
    main()

##-- end ifmain
