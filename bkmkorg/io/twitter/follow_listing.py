"""
script to get all users I follow, and create a file to annotate list membership
with details including bio
"""

import argparse
import logging as root_logger
import pickle
import textwrap
from functools import partial
from os import listdir
from os.path import exists, expanduser, isdir, isfile, join, splitext
from time import sleep

import twitter as tw
from bkmkorg.utils.twitter.api_setup import load_credentials_and_setup

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.user_listing"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

# Setup
parser = argparse.ArgumentParser("")
# todo: add output filename target
parser.add_argument('-t', '--target', default='output.org')
parser.add_argument('-b', '--backup', default='backup_')
parser.add_argument('-c', '--credentials', default="my.credentials")
parser.add_argument('-k', '--key', default="consumer.key")
parser.add_argument('-s', '--secret', default="consumer.secret")



##############################
#setup credentials
FIFTEEN_MINUTES  = 60 * 15
CHARWIDTH        = 80

def get_friends(twit, id_s=None):
    """ Given a twitter client, get my friends (ie: people I follow)
    friends/ids returns up to 5000, 15 times in 15 minutes
    """
    logging.info("Getting friends for: {}, type: {}".format(id_s, type(id_s)))
    #Gives up to 5000
    if id_s is not None:
        response = twit.friends.ids(user_id=id_s, stringify_ids="true")
    else:
        response = twit.friends.ids(stringify_ids="true")
    logging.info("Response length: {}".format(len(response['ids'])))
    return response['ids']

def get_users(twit, ids=None, writer=None, backup=None):
    """ Given a list of users, split into 100 user chunks,
    then GET users/lookup for them
    """
    batch_size = 100
    rate_limit = 300
    backup_file = "{}_retrieved".format(backup)
    #load the backup
    already_done = set()
    if exists(backup_file):
        logging.info("Retrieving processed record")
        with open(backup_file, 'r') as f:
            already_done = set(f.read().split('\n'))
    ids_set = list(set(ids).difference(already_done))
    chunked = [ids_set[x:x+batch_size] for x in range(0, len(ids_set), batch_size)]
    logging.info("After filtering, chunking {} into {}".format(len(ids), len(chunked)))

    loop_count = 0
    for i, chunk in enumerate(chunked):
        logging.info("Chunk {}".format(i))
        #request
        returned_data = twit.users.lookup(user_id=",".join(chunk))
        #parse data
        parsed_data = [user_obj_to_tuple(x) for x in returned_data]
        #call writer
        writer(parsed_data)
        #backup
        with open(backup_file, 'a') as f:
            f.write("\n".join(chunk))

        if loop_count < rate_limit:
            loop_count += 1
            sleep(5)
        else:
            loop_count = 0
            logging.info("Sleeping")
            sleep(FIFTEEN_MINUTES)

def init_file(filename):
    raise DeprecationWarning("Use TwitterUsersWriter")
    if exists(expanduser(filename)):
        return
    with open(expanduser(filename), 'a') as f:
        f.write("| User ID | Username | Tags | Verified |  Description|\n")
        f.write("|----|\n")

def append_to_file(filename, data):
    """ Append data to a given filename """
    raise DeprecationWarning("Use TwitterUsersWriter")
    with open(expanduser(filename), 'a') as f:
        for user_str, username, verified, description in data:
            safe_desc = textwrap.wrap(description.replace('|',''), CHARWIDTH)
            if not bool(safe_desc):
                safe_desc = [description]
            f.write("| {} | {} |  | {} | {} |\n".format(user_str,
                                                        username,
                                                        verified,
                                                        safe_desc[0]))
            for subline in safe_desc[1:]:
                f.write("| | | | | {} |\n".format(subline))
            f.write ("|-----|\n")

def user_obj_to_tuple(user_obj):
    id_str   = user_obj['id_str']
    name     = user_obj['screen_name']
    verified = user_obj['verified']
    desc     = user_obj['description']
    return (id_str, name, verified, desc)



if __name__ == "__main__":
    args = parser.parse_args()

    t = load_credentials_and_setup(args.credentials,
                                   args.key,
                                   args.secret)
    friends = []
    #Get all friends if you haven't already
    if not exists("{}_ids".format(args.backup)):
        friends = get_friends(t)
        with open("{}_ids".format(args.backup), 'w') as f:
            for id_str in friends:
                f.write("{}\n".format(id_str))
    else:
        with open('{}_ids'.format(args.backup),'r') as f:
            friends = f.read().split('\n')
    init_file(args.target)

    get_users(t, friends, partial(append_to_file, args.target), args.backup)
    logging.info("Retrieval complete")
