"""
script to create lists, and assign users to said lists
"""
import argparse
import logging as root_logger
import pickle
import textwrap
from collections import defaultdict
from functools import partial
from os import listdir
from os.path import exists, expanduser, isdir, isfile, join, splitext
from time import sleep

import regex as re

import twitter as tw
from bkmkorg.utils.twitter.api_setup import load_credentials_and_setup

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.list_uploading"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

# Setup
parser = argparse.ArgumentParser("")
# todo: add output filename target
parser.add_argument('-t', '--source', default='output.org')
parser.add_argument('-b', '--backup', default='backup_')
parser.add_argument('-c', '--credentials', default="my.credentials")
parser.add_argument('-k', '--key', default='consumer.key')
parser.add_argument('-s', '--secret', default='consumer.secret')


##############################
#setup credentials
FIFTEEN_MINUTES = 60 * 15
CHARWIDTH = 80

ORG_SPLIT = re.compile(r'\|')
DIVIDER_SPLIT = re.compile(r'\|[\-+]+\|')

def get_existing_lists(twit):
    logging.info("Getting Existing Lists")
    #use 1.1/lists/ownership.json
    #use cursoring
    all_lists = {}
    next_cursor = "-1"
    while next_cursor != '0':
        logging.info("Cursor: {}".format(next_cursor))
        response = twit.lists.ownerships(cursor=next_cursor)
        next_cursor = response['next_cursor_str']
        lists = response['lists']
        parsed_lists = {x['name'] : x['id'] for x in lists if 'belial42' in x['full_name']}
        all_lists.update(parsed_lists)
        sleep(20)

    return all_lists

def load_org(filename):
    logging.info("Loading Org")
    data = defaultdict(lambda: set([]))
    first = True
    columns = []
    user_id = None
    with open(filename, 'r') as f:
        for line in f:
            if first:
                # get boundaries
                first = False
                matches = [x.span()[0] for x in (ORG_SPLIT.finditer(line))]
                columns = list(zip(matches, matches[1:]))
                continue

            if DIVIDER_SPLIT.match(line):
                user_id = None
                continue

            #otherwise, split by into columns,
            maybe_id = line[columns[0][0]+1:columns[0][1]].strip()
            if maybe_id != '':
                logging.debug("Setting to ID: {}".format(maybe_id))
                user_id = maybe_id

            tags = [x.strip() for x in line[columns[2][0]+1:columns[2][1]].split(',') if bool(x.strip())]
            for tag in tags:
                data[tag].add(user_id)

    return dict(data)

def create_lists(twit, lists):
    logging.info("Creating Lists: {}".format(len(lists)))
    #use 1.1/lists/create.json
    to_create = lists[:]

    created = {}
    while to_create:
        current = to_create.pop(0)
        try:
            response = twit.lists.create(name=current, mode="private")
            created[response['name']] = response['id']
        except Exception as e:
            logging.warning("Creating list failed: {}".format(current))
            logging.warning("Remaining: {} / {}".format(len(to_create), len(lists)))
            logging.warning(e)
            to_create.append(current)
            sleep(30)
    return created

def chunks(l, n):
    """Yield successive n-sized chunks from l.
    https://stackoverflow.com/questions/312443
    from:
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]

def add_members(twit, list_name, list_id, members):
    logging.info("Adding members to: {}".format(list_name))
    #use 1.1/lists/members/create_all.json
    #rate limited
    #100 members at a time
    chunked = list(chunks(list(members), 100))
    while chunked:
        chunk = chunked.pop(0)
        try:
            twit.lists.members.create_all(list_id=list_id, user_id=", ".join(chunk))
            sleep(30)
        except Exception as e:
            logging.warning("Member add failure for : list_name")
            chunked.append(chunk)
            logging.warning("Remaining: {} / {}".format(len(chunked) * 100, len(members)))
            logging.warning(e)
            sleep(60)


if __name__ == "__main__":
    args = parser.parse_args()

    t = load_credentials_and_setup(args.credentials,
                                   args.key,
                                   args.secret)
    #Load the target
    the_dict = load_org(args.source)
    #get all existing lists
    existing_lists = get_existing_lists(t)
    #create them
    existing_lists.update(create_lists(t, [x for x in the_dict.keys() if x not in existing_lists]))
    #add users to each list
    for x,y in the_dict.items():
        add_members(t,x, existing_lists[x], y)
        sleep(30)
