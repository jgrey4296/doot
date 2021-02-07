#!/usr/bin/env python3

""" Bibtex utilities

"""
import logging as root_logger
logging = root_logger.getLogger(__name__)

import bibtexparser as b
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser

def make_parser(func):
    bparser = BibTexParser(common_strings=False)
    bparser.ignore_nonstandard_types = False
    bparser.homogenise_fields = True
    bparser.customization = func
    return bparser

def parse_bib_files(bib_files, func=None, database=None):
    """ Parse all the bibtext files into a shared database """
    bparser = make_parser(func)
    db = database
    if db is None:
        db = b.bibdatabase.BibDatabase()
    for x in bib_files:
        with open(x, 'r') as f:
            logging.info("Loading bibtex: {}".format(x))
            db = b.load(f, bparser)
    logging.info("Bibtex loaded")
    return db
