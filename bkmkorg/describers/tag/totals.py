#!/opt/anaconda3/envs/bookmark/bin/python
"""
Script to Process Bibtex, bookmark, and org files for tags
and to collect them
"""
import argparse
import logging as root_logger
import re
from os import mkdir
from os.path import abspath, expanduser, isdir, join, split, splitext

from bibtexparser import customization as c
from bkmkorg.io.reader.netscape import open_and_extract_bookmarks
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.file import retrieval
from bkmkorg.io.reader import tags as TR
from bkmkorg.utils.tag import clean
from bkmkorg.utils.tag.combine import combine_all_tags
from bkmkorg.io.writer.tags import write_tags

# Setup logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)



##############################
def custom(record):
    record = c.author(record)
    record = c.editor(record)
    tags = set()

    if 'tags' in record:
        tags.update([i.strip() for i in re.split(',|;', record["tags"].replace('\n', ''))])

    record['tags'] = tags
    record['p_authors'] = []
    if 'author' in record:
        record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    if 'editor' in record:
        record['p_authors'] = [c.splitname(x, False) for x in record['editor']]

    return record





if __name__ == "__main__":
    # Setup
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(["Extracts all tags in all bibtex, bookmark and org files in specified dirs"]))
    parser.add_argument('-t', '--target',action="append")
    parser.add_argument('-o', '--output', default="collected")
    parser.add_argument('-c', '--cleaned', action="append")

    logging.info("Tag Totals start: --------------------")
    cli_args = parser.parse_args()
    cli_args.output = abspath(expanduser(cli_args.output))

    logging.info("Targeting: {}".format(cli_args.target))
    if isdir(cli_args.output) and not exists(cli_args.output):
        mkdir(cli_args.output)
    if isdir(cli_args.output):
        cli_args.output = join(cli_args.output, "tags")
    logging.info("Output to: {}".format(cli_args.output))
    logging.info("Cleaned Tags locations: {}".format(cli_args.cleaned))

    bibs, htmls, orgs = retrieval.collect_files(cli_args.target)
    bib_db    = BU.parse_bib_files(bibs, func=custom)
    bib_tags  = TR.extract_tags_from_bibtex(bib_db)
    org_tags  = TR.extract_tags_from_org_files(orgs)
    html_tags = TR.extract_tags_from_html_files(htmls)
    all_tags  = combine_all_tags([bib_tags, org_tags, html_tags])

    write_tags(bib_tags, cli_args.output + "_bib")
    write_tags(org_tags, cli_args.output + "_orgs")
    write_tags(html_tags, cli_args.output + "_htmls")
    write_tags(all_tags, cli_args.output)
    logging.info("Complete --------------------")

    if not bool(cli_args.cleaned):
        exit()

    # load existing tag files
    cleaned_files = retrieval.get_data_files(cli_args.cleaned, [".txt", ".tags", ".org"])
    cleaned       = TR.read_substitutions(cleaned_files)

    # get new tags
    tags     = set(all_tags.keys())
    ctags    = set(cleaned.keys())
    new_tags = tags - ctags

    new_tag_dict = {x : all_tags[x] for x in new_tags}
    # group them separately, alphabeticaly
    # To be included in the separate tag files
    write_tags(new_tag_dict, cli_args.output + "_new")
