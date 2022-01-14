#!/usr/bin/env python3
## pylint: disable=protected-access
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

from os.path import exists, join, splitext, split
from os import listdir
import json
import requests
import uuid
import logging as root_logger
import twitter
logging = root_logger.getLogger(__name__)

from bkmkorg.utils.twitter.extraction import extract_tweet_ids_from_json

GROUP_AMNT = 100
MISSING    = ".missing_tweets"

def download_tweets(twit, json_dir, target_ids, lib_ids=None):
    """ Download all tweets and related tweets for a list,
    writing
    """
    logging.info("Downloading tweets to: {}".format(json_dir))
    logging.info("Reading existing tweet jsons")
    json_files = [join(json_dir, x) for x in listdir(json_dir) if splitext(x)[1] == ".json"]
    json_ids   = set()
    for jfile in json_files:
        json_ids.update(extract_tweet_ids_from_json(jfile))

    known_missing_tweets = set()
    if exists(join(json_dir, MISSING)):
        with open(join(json_dir, MISSING), 'r') as f:
            known_missing_tweets.update([x.strip() for x in f.readlines()])

    logging.info("Found {} existing tweet ids in jsons".format(len(json_ids)))
    logging.info("Found {} known missing tweet ids".format(len(known_missing_tweets)))
    # remove tweet id's already in library
    logging.info("Removing existing tweets from queue")
    if lib_ids is None:
        lib_ids = set()

    remaining = (target_ids - lib_ids)
    remaining.difference_update(json_ids)
    remaining.difference_update(known_missing_tweets)
    logging.info("Remaining ids to process: {}".format(len(remaining)))

    if not bool(remaining):
        return True

    queue = list(remaining)
    # Loop:
    while bool(queue):
        logging.info("Queue loop: {}".format(len(queue)))
        # Pop group amount:
        current = set(queue[:GROUP_AMNT])
        current -= json_ids
        current = list(current)
        queue   = queue[GROUP_AMNT:]

        ## download tweets
        results = twit.GetStatuses(current, trim_user=True)

        # add results to results dir
        new_json_file = join(json_dir, "{}.json".format(uuid.uuid1()))
        assert(not exists(new_json_file))
        with open(new_json_file, 'w') as f:
            as_json = "[{}]".format(",".join([json.dumps(x._json, indent=4) for x in results]))
            f.write(as_json)

        # update ids
        json_ids.update([x.id_str for x in results])

        # Add new referenced ids:
        for x in results:
            if 'in_reply_to_status_id_str' in x._json and x._json['in_reply_to_status_id_str'] is not None:
                queue.append(str(x._json['in_reply_to_status_id_str']))
            if 'quoted_status_id_str' in x._json and x._json['quoted_status_id_str'] is not None:
                queue.append(x._json['quoted_status_id_str'])

        # Store missing ids
        not_retrieved = set(current).difference([x._json['id_str'] for x in results])
        known_missing_tweets.update(not_retrieved)

        with open(join(json_dir, MISSING), 'a') as f:
            f.write("\n".join(known_missing_tweets))

    return False

def get_user_identities(users_file, twit, users) -> Dict[str, Any]:
    """ Get all user identities from twitter """
    logging.info("Getting user identities")
    total_users = {}
    user_queue  = list(users)
    if exists(users_file):
        with open(users_file,'r') as f:
            total_users.update({x['id_str'] : x for x in  json.load(f, strict=False)})

        users -= total_users.keys()
        logging.info("Already retrieved {}, {} remaining".format(len(total_users), len(users)))
        user_queue = list(users)

    while bool(user_queue):
        current = user_queue[:100]
        user_queue = user_queue[100:]

        try:
            data = twit.UsersLookup(user_id=current)
            logging.info("Retrieved: {}".format(len(data)))
            new_users = [json.loads(x.AsJsonString()) for x in data]
            total_users.update({x['id_str'] : x for x in new_users})

        except twitter.error.TwitterError as err:
            logging.info("Does not exist: {}".format(current))


    with open(users_file, 'w') as f:
        json.dump(list(total_users.values()), f, indent=4)

    return total_users
