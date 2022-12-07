#!/usr/bin/env python3
## pylint: disable=protected-access
##-- imports
from __future__ import annotations

import pathlib as pl
import json
import logging as root_logger
import uuid
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import requests
import twitter
from bkmkorg.twitter.extraction import extract_tweet_ids_from_json
##-- end imports

logging    = root_logger.getLogger(__name__)
GROUP_AMNT = 100
MISSING    = ".missing_tweets"

def download_tweets(twit, json_dir:pl.Path, target_ids, lib_ids=None):
    """ Download all tweets and related tweets for a list,
    writing
    """
    logging.info("Downloading tweets to: %s", json_dir)
    logging.info("Reading existing tweet jsons")
    json_files = [x for x in json_dir.iterdir() if x.suffix == ".json"]
    json_ids   = set()
    for jfile in json_files:
        json_ids.update(extract_tweet_ids_from_json(jfile))

    known_missing_tweets = set()
    if (json_dir / MISSING).exists():
        with open(json_dir / MISSING, 'r') as f:
            known_missing_tweets.update([x.strip() for x in f.readlines()])

    logging.info("Found %s existing tweet ids in jsons", len(json_ids))
    logging.info("Found %s known missing tweet ids", len(known_missing_tweets))
    # remove tweet id's already in library
    logging.info("Removing existing tweets from queue")
    if lib_ids is None:
        lib_ids = set()

    remaining = (target_ids - lib_ids)
    remaining.difference_update(json_ids)
    remaining.difference_update(known_missing_tweets)
    logging.info("Remaining ids to process: %s", len(remaining))

    if not bool(remaining):
        return True

    queue = list(remaining)
    # Loop:
    while bool(queue):
        logging.info("Queue loop: %s", len(queue))
        # Pop group amount:
        current = set(queue[:GROUP_AMNT])
        current -= json_ids
        current = list(current)
        queue   = queue[GROUP_AMNT:]

        ## download tweets
        results = twit.GetStatuses(current, trim_user=True)

        # add results to results dir
        new_json_file = json_dir / f"{uuid.uuid4().hex}.json"
        assert(not new_json_file.exists())
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

        with open(json_dir / MISSING, 'a') as f:
            f.write("\n".join(known_missing_tweets))

    return False

