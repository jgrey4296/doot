#!/usr/bin/env python
""" Bibtex utilities

"""
import logging as root_logger

import bibtexparser as b
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser

logging = root_logger.getLogger(__name__)

class OverrideDict(dict):
    """
    A Simple dict that doesn't error if a key isn't found.
    Used to avoid UndefinedString Exceptions in bibtex parsing
    """

    def __getitem__(self, k):
        if k not in self:
            logging.warning("Adding string to override dict: %s", k)
            self[k] = k
        return k

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
        logging.info("Creating new database")
        db = b.bibdatabase.BibDatabase()

    db.strings = OverrideDict()

    bparser.bib_database = db
    for x in bib_files:
        try:
            with open(x, 'r') as f:
                logging.info(f"Loading bibtex: {x}")
                bparser.parse_file(f, partial=True)
        except Exception as err:
            logging.warning(f"Error for: {x}: {err}")
    logging.info("Bibtex loaded")
    return db
