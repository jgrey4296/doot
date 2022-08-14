#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import logging as root_logger
import pathlib as pl
from datetime import datetime
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import regex as re
##-- end imports

logging = root_logger.getLogger(__name__)

img_exts      = {".jpg",".jpeg",".png",".gif",".webp",".tiff"}
img_exts2     = img_exts | {".mp4",".bmp"}
img_and_video = img_exts2  | {".mov", ".avi", ".webp"}

def dfs_directory(*dirs:str|pl.Path, ext:None|str|set[str]=None):
    """ DFS a directory for a filetype """
    logging.info("DFSing {}".format(dirs))
    if ext is None:
        ext = ".org"
    found = []
    queue = [pl.Path(x).expanduser().resolve() for x in dirs]

    while bool(queue):
        current = queue.pop(0)
        assert(current.exists())
        # Add files
        if current.is_file() and current.suffix in ext:
            found.append(current)
        else:
            queue += [x for x in current.iterdir() if x != ".git"]

    return found

def collect_files(targets:list[str|pl.Path]):
    """ DFS targets, collecting files into their types """
    logging.info("Processing Files: %s", targets)
    bib_files      = set()
    html_files     = set()
    bookmark_files = set()
    org_files      = set()

    processed      = set([])
    remaining_dirs = [pl.Path(x).expanduser().resolve() for x in targets]

    while bool(remaining_dirs):
        target = remaining_dirs.pop(0)
        assert(target.exists())
        if target in processed:
            continue
        processed.add(target)
        if target.is_file():
            match target.suffix:
                case ".bib":
                    bib_files.add(target)
                case ".html":
                    html_files.add(target)
                case ".org":
                    org_files.add(target)
                case ".bookmarks":
                    bookmark_files.add(target)
                case _:
                    logging.debug("Found unrecognized extension: %s", target.suffix)
        else:
            assert(target.is_dir()), target
            remaining_dirs += [x for x in target.iterdir()]

    logging.info("Split into: {} bibtex files, {} html files and {} org files".format(len(bib_files),
                                                                                      len(html_files),
                                                                                      len(org_files)))
    logging.debug("Bibtex files: %s"   , "\n".join(str(x) for x in bib_files))
    logging.debug("Html Files: %s"     , "\n".join(str(x) for x in html_files))
    logging.debug("Org Files: %s"      , "\n".join(str(x) for x in org_files))
    logging.debug("Bookmark Files: %s" , "\n".join(str(x) for x in bookmark_files))

    return (bib_files, html_files, org_files, bookmark_files)

def get_data_files(initial:str|pl.Path, ext=None) -> list[str]:
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
    queue = [pl.Path(x).expanduser().resolve() for x in initial]
    while bool(queue):
        current : pl.Path = queue.pop(0)
        assert(current.exists())
        ftype             = current.suffix
        match_type        = not bool(ext) or ftype in ext
        missing_type      = ftype not in unrecognised_types

        if current.is_file() and match_type:
            files.append(current)
        elif current.is_file() and not match_type and missing_type:
            logging.warning("Unrecognized file type: %s", current.name)
            unrecognised_types.add(ftype)
        elif current.is_dir():
            queue += [x for x in current.iterdir()]


    logging.info("Found %s %s files", len(files), ext)
    return files
