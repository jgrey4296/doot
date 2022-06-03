#!/usr/bin/env python3
import logging as root_logger
from datetime import datetime
from os import listdir, mkdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from unicodedata import normalize as norm_unicode

import regex as re

logging = root_logger.getLogger(__name__)

img_exts      = [".jpg",".jpeg",".png",".gif",".webp",".tiff"]
img_exts2     = [".gif",".jpg",".jpeg",".png",".mp4",".bmp"]
img_and_video = [".gif",".jpg",".jpeg",".png",".mp4",".bmp", ".mov", ".avi", ".webp", ".tiff"]

def dfs_directory(*dirs, ext=None):
    """ DFS a directory for a filetype """
    logging.info("DFSing {}".format(dirs))
    if ext is None:
        ext = ".org"
    found = []
    queue = [] + list(dirs)

    while bool(queue):
        current = queue.pop(0)
        # Add files
        if isfile(current) and splitext(current)[1] == ext:
            found.append(current)
        else:
            listed = listdir(current)
            found += [join(current, x) for x in listed
                      if isfile(join(current, x)) and splitext(x)[1] == ext]
            # Continue for directories
            queue += [join(current, x) for x in listed
                      if isdir(join(current, x)) and x != ".git"]

    return found

def collect_files(targets):
    """ DFS targets, collecting files into their types """
    logging.info("Processing Files: {}".format(targets))
    bib_files      = set()
    html_files     = set()
    bookmark_files = set()
    org_files      = set()

    processed      = set([])
    remaining_dirs = [abspath(expanduser(x)) for x in targets]

    while bool(remaining_dirs):
        target = remaining_dirs.pop(0)
        if target in processed:
            continue
        processed.add(target)
        if isfile(target):
            ext = splitext(target)[1]
            if ext == ".bib":
                bib_files.add(target)
            elif ext == ".html":
                html_files.add(target)
            elif ext == ".org":
                org_files.add(target)
            elif ext == ".bookmarks":
                bookmark_files.add(target)
        else:
            assert(isdir(target)), target
            subdirs = [join(target, x) for x in listdir(target)]
            remaining_dirs += subdirs

    logging.info("Split into: {} bibtex files, {} html files and {} org files".format(len(bib_files),
                                                                                      len(html_files),
                                                                                      len(org_files)))
    logging.debug("Bibtex files: {}".format("\n".join(bib_files)))
    logging.debug("Html Files: {}".format("\n".join(html_files)))
    logging.debug("Org Files: {}".format("\n".join(org_files)))
    logging.debug("Bookmark Files: {}".format("\n".join(bookmark_files)))

    return (bib_files, html_files, org_files, bookmark_files)

def get_data_files(initial, ext=None, normalize=False):
    """
    DFS, Getting all files of an extension
    """
    logging.info("Getting Data Files")
    ext = ext or []

    if not isinstance(ext, list):
        ext = [ext]
    if not isinstance(initial, list):
        initial = [initial]

    unrecognised_types = set()
    files = []
    queue = [abspath(expanduser(x)) for x in initial]
    while bool(queue):
        current = queue.pop(0)
        ftype = splitext(current)[1].lower()
        match_type = not bool(ext) or ftype in ext
        missing_type = ftype not in unrecognised_types

        if isfile(current) and match_type:
            files.append(current)
        elif isfile(current) and not match_type and missing_type:
            logging.warning("Unrecognized file type: {}".format(split(current)[1]))
            unrecognised_types.add(ftype)
        elif isdir(current):
            sub = [join(current,x) for x in listdir(current)]
            queue += sub


    logging.info("Found {} {} files".format(len(files), ext))
    if normalize:
        files = [norm_unicode("NFD", x) for x in files]
    return files
