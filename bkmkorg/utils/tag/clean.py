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
from bkmkorg.utils.bookmarks.collection import Bookmark


logging = root_logger.getLogger(__name__)


def clean_bib_files(bib_files, sub, tag_regex=r"^(\s*tags\s*=\s*{)(.+?)(\s*},?)$"):
    """ Parse all the bibtext files, naively
    Extract the tags, deduplicate and apply substitutions,
    write out again
    """
    TAG_REGEX = re.compile(tag_regex)

    for bib in bib_files:
        lines = []
        out_lines = []
        with open(bib, 'r') as f:
            lines = f.readlines()
        logging.debug("File loaded")

        for line in lines:
            match = TAG_REGEX.match(line)

            if match is None:
                out_lines.append(line)
                continue

            tags = [x.strip() for x in match[2].split(",") if bool(x.strip())]
            replacement_tags = set()
            for tag in tags:
                replacement_tags.add(sub.get_sub(tag))

            out_lines.append("{}{}{}\n".format(match[1],
                                               ",".join(sorted(replacement_tags)),
                                               match[3]))

        outstring = "".join(out_lines)
        with open(bib, 'w') as f:
            f.write(outstring)

def clean_org_files(org_files, sub, tag_regex=r"^\*\*\s+(.+?)(\s+):(\S+):$"):
    """
    Read all org files, matching on headings,
    and deduplicate and substitute, write out again
    """
    logging.info("Cleaning orgs")
    ORG_TAG_REGEX = re.compile(tag_regex)

    for org in org_files:
        #read
        text = []
        with open(org,'r') as f:
            text = f.readlines()

        out_text = ""
        #line by line
        for line in text:
            matches = ORG_TAG_REGEX.match(line)

            if not bool(matches):
                out_text += line
                continue

            title = matches[1]
            spaces = matches[2]
            tags = matches[3]

            individual_tags = [x for x in tags.split(':') if x != '']
            replacement_tags = set([])
            #swap to dict:
            for tag in individual_tags:
                replacement_tags.add(sub.get_sub(tag))

            out_line = "** {}{}:{}:\n".format(title,
                                              spaces,
                                              ":".join(sorted(replacement_tags)))
            out_text += out_line
        # write out
        with open(org, 'w') as f:
            f.write(out_text)

def clean_bkmk_files(bkmk_files, sub):
    logging.info("Cleaning bookmarks")

    for bkmk_path in bkmk_files:
        cleaned   = []
        with open(bkmk_path, 'r') as f:
            bookmarks = BookmarkCollection.read(f)

        for bkmk in bkmks:
            bkmk.clean(sub)

        with open(bkmk_path, 'w') as f:
            f.write(str(bookmarks))
