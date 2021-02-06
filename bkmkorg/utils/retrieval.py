#!/usr/bin/env python3

"""
Utilities to retrieve files of use

"""
import logging as root_logger
from os import listdir, mkdir
from os.path import join, isfile, exists, isdir, splitext, expanduser, abspath, split

logging = root_logger.getLogger(__name__)
img_exts = [".jpg",".jpeg",".png",".gif",".webp",".tiff"]
img_exts2 = [".gif",".jpg",".jpeg",".png",".mp4",".bmp"]
img_and_video = [".gif",".jpg",".jpeg",".png",".mp4",".bmp", ".mov", ".avi", ".webp", ".tiff"]

def collect_files(targets):
    """ DFS targets, collecting files into their types """
    logging.info("Processing Files: {}".format(targets))
    bib_files      = set()
    html_files     = set()
    org_files      = set()

    processed      = set([])
    remaining_dirs = targets[:]

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
        else:
            assert(isdir(target))
            subdirs = [join(target, x) for x in listdir(target)]
            remaining_dirs += subdirs

    logging.info("Split into: {} bibtex files, {} html files and {} org files".format(len(bib_files),
                                                                                      len(html_files),
                                                                                      len(org_files)))
    logging.debug("Bibtex files: {}".format("\n".join(bib_files)))
    logging.debug("Html Files: {}".format("\n".join(html_files)))
    logging.debug("Org Files: {}".format("\n".join(org_files)))

    return (bib_files, html_files, org_files)

def get_data_files(initial, ext):
    """
    Getting all files of an extension
    """
    logging.info("Getting Data Files")
    if not isinstance(ext, list):
        ext = [ext]
    if not isinstance(initial, list):
        initial = [initial]

    unreognized_types = set()
    files = []
    queue = initial[:]
    while bool(queue):
        current = queue.pop(0)
        ftype = splitext(current)[1].lower()
        if isfile(current) and ftype in ext:
            files.append(current)
        elif isfile(current) and ftype not in ext and ftype not in unrecognised_types:
            logging.warning("Unrecognized file type: {}".format(splitext(current)[1].lower()))
            unrecognised_types.add(ftype)
        elif isdir(current):
            sub = [join(current,x) for x in listdir(current)]
            queue += sub


    logging.info("Found {} {} files".format(len(files), ext))
    return files



def read_raw_tags(target, org=False):
    """ Read a text file of the form:
    tag : num : sub : sub : sub....
    returning a dict of {tag : [sub]}
    """
    lines = []
    sub = {}
    with open(target,'r') as f:
        lines = f.readlines()

    #split and process
    for line in lines:
        if org and line[0] == "*":
            continue
        components = line.split(":")
        component_zero = components[0].strip()
        if component_zero == "":
            continue

        assert(component_zero not in sub)
        sub[component_zero] = []
        if len(components) > 2:
            sub[component_zero] += [x.strip() for x in components[2:]]

    return sub





def clean_bib_files(bib_files, sub, tag_regex="^(\s*tags\s*=\s*{)(.+?)(\s*},?)$"):
    """ Parse all the bibtext files
    Extract the tags, deduplicate and apply substitutions , write out again

    """
    TAG_REGEX = regex.compile(tag_regex)

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

def check_orgs(org_files, id_regex="^\s+:(PERMALINK|TIME):\s+$"):
    logging.info("Checking Orgs")
    ORG_ID_REGEX = regex.compile(id_regex)
    files = set([])

    for org in org_files:
        #read
        text = []
        with open(org,'r') as f:
            text = f.readlines()

        #line by line
        for line in text:
            match = ORG_ID_REGEX.match(line)
            if not bool(match):
                continue

            files.add(org)
            break

    return files



def extract_ids_from_orgs(org_files, id_regex="^\s+:PERMALINK:\s+\[\[.+?/(\d+)\]"):
    logging.info("Extracting data from orgs")
    ids = set([])
    ORG_ID_REGEX = regex.compile(id_regex)
    for org in org_files:
        #read
        text = []
        with open(org,'r') as f:
            text = f.readlines()

        #line by line
        for line in text:
            match = ORG_ID_REGEX.match(line)
            individual_ids = []
            if not bool(match):
                continue

            id_str = match[1]
            ids.add(id_str)

    return ids
