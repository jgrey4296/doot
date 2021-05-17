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

def read_substitutions(target: Union[str, List[str]], counts=True) -> Dict[str, List[str]]:
    """ Read a text file of the form (with counts):
    tag : num : sub : sub : sub....
    without counts:
    tag : sub : sub : ...
    returning a dict of {tag : [sub]}
    """
    if isinstance(target, str):
        target = [target]

    assert(all([splitext(x)[1] in [".tags", ".txt", ".org"] for x in target]))
    sub = {}

    for path in target:
        logging.info("Reading Raw Tag Subs: {}".format(path))
        is_org = splitext(path)[1] == ".org"
        lines = []
        with open(path,'r') as f:
            lines = f.readlines()

        #split and process
        for line in lines:
            # Discard org headings:
            if is_org and line[0] == "*":
                continue
            components = line.split(":")
            # Get the pattern:
            component_zero = components[0].strip()
            if component_zero == "":
                continue

            assert(component_zero not in sub)
            sub[component_zero] = []
            # Get the substitutions
            sub_start = 1 if counts else 2
            if len(components) > 1:
                sub[component_zero] += [x.strip() for x in components[sub_start:]]
            else:
                logging.warning("No Substitutions found for: {}".format(component_zero))

    return sub


def clean_bib_files(bib_files, sub, tag_regex="^(\s*tags\s*=\s*{)(.+?)(\s*},?)$"):
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

            tags = [x.strip() for x in match[2].split(",")]
            replacement_tags = set([])
            for tag in tags:
                if tag in sub and bool(sub[tag]):
                    [replacement_tags.add(new_tag) for new_tag in sub[tag]]
                else:
                    replacement_tags.add(tag)
            out_lines.append("{}{}{}\n".format(match[1],
                                               ",".join(replacement_tags),
                                               match[3]))

        outstring = "".join(out_lines)
        with open(bib, 'w') as f:
            f.write(outstring)

def clean_org_files(org_files, sub, tag_regex="^\*\*\s+(.+?)(\s+):(\S+):$"):
    """
    Read all org files, matching on headings,
    and deduplicate and substitute, write out again
    """
    logging.info("Cleaning orgs")
    org_tags = {}

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
                if tag in sub and bool(sub[tag]):
                    [replacement_tags.add(new_tag) for new_tag in sub[tag]]
                else:
                    replacement_tags.add(tag)

            out_line = "** {}{}:{}:\n".format(title,
                                              spaces,
                                              ":".join(replacement_tags))
            out_text += out_line
        # write out
        with open(org, 'w') as f:
            f.write(out_text)

def clean_html_files(html_files, sub):
    """
    Read all htmls,
    apply substitutions
    """
    logging.info("Cleaning htmls")
    html_tags = {}

    for html in html_files:
        bkmks = open_and_extract_bookmarks(html)
        cleaned_bkmks = []
        for bkmk in bkmks:
            replacement_tags = set([])
            for tag in bkmk.tags:
                # clean
                if tag in sub and bool(sub[tag]):
                    [replacement_tags.add(new_tag) for new_tag in sub[tag]]
                else:
                    replacement_tags.add(tag)
            new_bkmk = bookmarkTuple(bkmk.name, bkmk.url, replacement_tags)
            cleaned_bkmks.append(new_bkmk)
        # write out
        exportBookmarks(cleaned_bkmks, html)
