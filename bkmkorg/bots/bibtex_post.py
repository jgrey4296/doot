#!/opt/anaconda3/envs/bookmark/bin/python
# Setup root_logger:
from __future__ import annotations

import argparse
import json
import logging as root_logger
import subprocess
from configparser import ConfigParser
from importlib.resources import files
from os import listdir, system
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from random import choice

import bibtexparser as b
import twitter
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bkmkorg import DEFAULT_BOTS, DEFAULT_CONFIG
from bkmkorg.utils.mastodon.api_setup import setup_mastodon
from bkmkorg.utils.twitter.api_setup import setup_twitter

data_path = files(f"bkmkorg.{DEFAULT_CONFIG}")
data_bots= data_path.joinpath(DEFAULT_BOTS)

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.WARN)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Auto Tweet/Toot a Bibtex entry"]))
parser.add_argument('-c', '--config', default=data_bots,
                    help="The Config File to Use")

args     = parser.parse_args()

expander = lambda x: abspath(expanduser(x))

config   = ConfigParser(allow_no_value=True, delimiters='=')
# Read the main config
config.read(expander(args.config))
# Then read in secrets
config.read(data_path.joinpath(config['DEFAULT']['secrets_loc']))

MAX_ATTEMPTS = int(config['DEFAULT']['MAX_ATTEMPTS'])
TWEET_LEN    = int(config['DEFAULT']['tweet_len'])
TOOT_LEN     = int(config['DEFAULT']['toot_len'])

BIBTEX_LIB   = expander(config['BIBTEX']['lib'])
BLACKLIST    = data_path.joinpath(config['BIBTEX']['blacklist'])
SUCCESS_LOG  = data_path.joinpath(config['BIBTEX']['success_log'])
FAIL_LOG     = data_path.joinpath(config['BIBTEX']['fail_log'])

def select_bibtex():
    # logging.info("Selecting bibtex")
    # load blacklist
    with open(BLACKLIST, 'r') as f:
        blacklist = [x.strip() for x in f.readlines() if bool(x.strip())]


    bibs = [x for x in listdir(BIBTEX_LIB) if splitext(x)[1] == ".bib"]
    filtered = [x for x in bibs if x not in blacklist]

    assert(len(filtered) <= len(bibs))
    selected = join(BIBTEX_LIB, choice(filtered))

    return selected

def parse_bibtex(file_path):
    # logging.info("Parsing: {}".format(file_path))
    with open(expander(file_path)) as f:
        database = b.load(f)

    return database

def select_entry(db, already_tweeted, filename):
    # logging.info("Selecting Entry")
    entry = None
    tried_alts = 0
    required_keys = config['BIBTEX_KEYS']['required'].split(" ")
    one_of_keys   = config['BIBTEX_KEYS']['one_of'].split(" ")

    while entry is None and tried_alts < len(db.entries) and tried_alts < MAX_ATTEMPTS:
        poss_entry = choice(db.entries)
        tried_alts += 1

        has_keys = all([x in poss_entry for x in required_keys])
        one_of = any([x in poss_entry for x in one_of_keys])
        not_tweeted_before = poss_entry['ID'] not in already_tweeted

        if has_keys and one_of and not_tweeted_before:
            entry = poss_entry

    if entry is None:
        logging.warning(f"No Appropriate Entry Found for db: {filename}")

    return entry

def maybe_blacklist_file(db, file_path, already_tweeted):
    one_of_keys   = config['BIBTEX_KEYS']['one_of'].split(" ")
    has_fields       = lambda poss_entry: any([x in poss_entry for x in one_of_keys])
    not_tweeted_yet  = lambda poss_entry: poss_entry['ID'] not in already_tweeted

    sufficient_entry = lambda entry: has_fields(entry) and not_tweeted_yet(entry)

    with open(BLACKLIST, 'r') as f:
        blacklisted = [x.strip() for x in f.readlines()]

    assert(file_path not in blacklisted)
    if not any([sufficient_entry(x) for x in db.entries]):
        logging.info(f"Bibtex failed check, blacklisting: {file_path}")
        with open(BLACKLIST, 'a') as f:
            f.write(f"{split(file_path)[1]}\n")

    exit()


def format_tweet(entry):
    # TODO convert strings to appropriate unicode
    # logging.info("Formatting Entry")

    author = entry['author']
    if len(author) > 30:
        author = f"{author[:30]}..."

    result = f"{entry['title']}\n"
    result += f"({entry['year']}) : {entry['author']}\n"
    if "doi" in entry:
        result += f"DOI: https://doi.org/{entry['doi']}\n"
    elif "url" in entry:
        result += f"url: {entry['url']}\n"
    elif "isbn" in entry:
        result += f"isbn: {entry['isbn']}\n"
    else:
        logging.warning(f"Bad Entry: {entry['ID']}")
        exit()

    tags = " ".join(["#{}".format(x.strip()) for x in entry['tags'].split(',')])
    if len(result) <= 250:
        diff = 250 - len(result)
        result += tags[:diff]

    result += "\n#my_bibtex"

    return (entry['ID'], result)

def main():
    # logging.info("Running Auto Bibtex Tweet")
    with open(SUCCESS_LOG) as f:
        tweeted = [x.strip() for x in f.readlines()]

    bib        = select_bibtex()
    db         = parse_bibtex(bib)
    entry      = select_entry(db, tweeted, bib)

    if entry is None:
        maybe_blacklist_file(db, bib, tweeted)

    id_str, tweet_text = format_tweet(entry)

    twit     = setup_twitter(config)
    mastodon = setup_mastodon(config)

    success = False
    try:
        if len(tweet_text) >= TWEET_LEN:
            logging.warning(f"Resulting Tweet too long for twitter: {len(tweet_text)}\n{tweet_text}")
        else:
            result = twit.PostUpdate(tweet_text)
            success |= True
    except Exception as err:
        logging.warning(f"Twitter Post Failure: {err}")

    try:
        if len(tweet_text) >= TOOT_LEN:
            logging.warning(f"Resulting Tweet too long for mastodon: {len(tweet_text)}\n{tweet_text}")
        else:
            result = mastodon.status_post(tweet_text)
            success |= True
    except Exception as err:
        logging.warning(f"Mastodon Post Failure: {err}")

    if success:
        with open(SUCCESS_LOG, 'a') as f:
            f.write(f"{id_str}\n")

    else:
        single_line = tweet_text.replace("\n", "")
        # If the tweet is too long, log it as as single line
        with open(FAIL_LOG, 'a') as f:
            f.write(f"({id_str}) : {single_line}\n")

if __name__ == "__main__":
    main()
