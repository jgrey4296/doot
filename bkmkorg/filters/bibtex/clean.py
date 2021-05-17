"""
Script to clean a bibtex file, converting everything to unicode
"""
import argparse
import logging as root_logger
from hashlib import sha256
from math import ceil
from os import listdir, mkdir
from os.path import (abspath, commonpath, exists, expanduser, isdir, isfile,
                     join, realpath, split, splitext)
from shutil import copyfile, move

import bibtexparser as b
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.file import retrieval

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

def add_slash_if_necessary(x):
    if x[0] != '/' and x[0] != "~":
        x = '/' + x
    return x.strip()

def safe_splitname(s):
    s = s.strip()
    if s.endswith(","):
        s = s[:-1]
    return c.splitname(s)

def custom(record):
    try:
        record = c.convert_to_unicode(record)
    except TypeError as e:
        logging.warning("Unicode Error on: {}".format(record['ID']))
        record['error'] = str(e)
        file_set = None
    try:
        #add md5 of associated files
        files = [add_slash_if_necessary(y) for x in record['file'].split(';') for y in x.split(':') if bool(y.strip()) and y.strip().lower() != 'pdf']
        file_set = set(files)
        if not 'hashes' in record:
            hashes = [file_to_hash(x) for x in file_set]
            record['hashes'] = ";".join(hashes)
            #regularize format of files list
            record['file'] = ";".join(file_set)
        else:
            saved_hashes = set(record['hashes'].split(';'))
            hashes = set([file_to_hash(x) for x in file_set])
            if saved_hashes.symmetric_difference(hashes):
                raise Exception("Hash Mismatches", saved_hashes.difference(hashes), hashes.difference(saved_hashes))

    except FileNotFoundError as e:
        logging.warning("File Error: {} : {}".format(record['ID'], e.args[0]))
        record['error'] = "File Error: {}".format(e.args[0])
    except Exception as e:
        logging.warning("Error: {}".format(e.args[0]))
        record['error'] = "{} : / :".format(e.args[0], e.args[1])

    #if file is not in the library common prefix, move it there
    #look for year, then first surname, then copy in, making dir if necessary
    if file_set:
        for x in file_set:
            try:
                logging.info("Expanding: {}".format(x))
                current_path = abspath(expanduser(x))
                common = commonpath([current_path, args.library])
                if common != args.library:
                    logging.info("Found file outside library: {}".format(current_path))
                    logging.info("Common: {}".format(common))
                    #get the author and year
                    year = record['year']
                    authors = c.getnames([i.strip() for i in record["author"].replace('\n', ' ').split(" and ")])
                    authors_split = [safe_splitname(a) for a in authors]
                    author_surnames = [a['last'][0] for a in authors_split]
                    year_path = join(args.library, year)
                    author_path = join(year_path, ", ".join(author_surnames))
                    logging.info("New Path: {}".format(author_path))
                    #create directory if necessary
                    #copy file
                    full_new_path = join(author_path, split(current_path)[1])
                    logging.info("Copying file")
                    logging.info("From: {}".format(current_path))
                    logging.info("To: {}".format(full_new_path))
                    response = input("Enter to confirm: ")
                    if response == "":
                        logging.info("Proceeding")
                        if not exists(year_path):
                            mkdir(year_path)
                        if not exists(author_path):
                            mkdir(author_path)
                        if not exists(full_new_path):
                            copyfile(current_path, full_new_path)
                            move(current_path, "{}__x".format(current_path))
                            file_set.remove(x)
                            file_set.add(full_new_path)
                            record['file'] = ";".join(file_set)
            except Exception as e:
                logging.info("Issue copying file for: {}".format(x))
                logging.info(e)
                record['error'] = str(e)

    #regularize keywords
    try:
        keywords = set()
        if 'tags' not in record:
            if 'keywords' in record:
                keywords.update([x.strip() for x in record['keywords'].split(',')])
                del record['keywords']
            if 'mendeley-tags' in record:
                keywords.update([x.strip() for x in record['mendeley-tags'].split(',')])
                del record['mendeley-tags']

            record['tags'] = ",".join(keywords)
    except Error as e:
        logging.warning("Tag Error: {}".format(record['ID']))
        record['error'] = 'tag'

    # record = c.type(record)
    # record = c.author(record)
    # record = c.editor(record)
    # record = c.journal(record)
    # record = c.keyword(record)
    # record = c.link(record)
    # record = c.doi(record)
    # record['p_authors'] = []
    # if 'author' in record:
    #     record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record


if __name__ == "__main__":
    # Setup
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=
                                     "\n".join(["Specify a Target bibtex file,",
                                                "Output file,",
                                                "And the Location of the pdf library.",
                                                "Cleans names and moves all non-library pdfs into the library.",
                                                "Records errors in an 'error' field for an entry."]))

    parser.add_argument('-t', '--target', action='append')
    parser.add_argument('-o', '--output', default="bibtex")
    parser.add_argument('-l', '--library', default="~/MEGA/pdflibrary")
    args = parser.parse_args()

    assert(exists(args.target))

    logging.info("Targeting: {}".format(args.target))
    logging.info("Output to: {}".format(args.output))

    bib_files = retrieval.get_data_files(args.target, ".bib")
    db = BU.parse_bib_files(bib_files, func=custom)

    #Get errors and write them out:
    errored = [x for x in db.entries if 'error' in x]

    with open('{}.errors'.format(args.output), 'a') as f:
        f.write("\n".join(["{} : {}".format(x['ID'], x['error']) for x in errored]))

    writer = BibTexWriterr()
    with open(args.output,'w') as f:
        f.write(writer.write(db))
