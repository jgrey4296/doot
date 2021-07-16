from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

import re
from os.path import exists, splitext, join, isfile, isdir
from os import listdir
import json

import logging as root_logger

from bkmkorg.io.twitter.dfs_utils import dfs_directory

logging = root_logger.getLogger(__name__)


PERMALINK_RE = re.compile(r"\[.+?/status/(\d+)\]\]")

def extract_tweet_ids_from_file(the_file, simple=False):
    """ Get all mentioned tweets in a file.
    Can search for regexs, or treat file as a line list of urls """
    use_regex = PERMALINK_RE
    if simple:
        use_regex = re.compile(r"/status/(\d+)")

    exists(the_file)
    with open(the_file, 'r') as f:
        lines = f.readlines()

    # grep file lines for permalinks
    results = set()
    for line in lines:
        match = use_regex.search(line)
        if match is not None:
            results.add(match[1])

    return results

def extract_tweet_ids_from_json(the_file):
    """ Get all tweet ids from a json file """
    try:
        with open(the_file, 'r') as f:
            data = json.load(f, strict=False)
    except Exception as e:
        logging.info("File issue: {}".format(the_file))
        raise e

    ids = [x['id_str'] for x in data]
    return ids

def extract_media_and_users_from_json(the_file):
    """ Get all media urls and user ids from json file """
    try:
        with open(the_file, 'r') as f:
            data = json.load(f, strict=False)
    except Exception as e:
        logging.info("File issue: {}".format(the_file))
        raise e

    ids            = set()
    media          = set()
    media_variants = []
    for x in data:
        if 'entities' in x and 'media' in x['entities']:
            entities = x['entities']
            media.update([m['media_url'] for m in entities['media']])

            videos = [m['video_info'] for m in entities['media'] if m['type'] == "video"]
            for video in videos:
                urls = [n['url'] for n in video['variants'] if n['content_type'] == "video/mp4"]
                trimmed = [x.split("?")[0] for x in urls]
                media.update(trimmed)
                media_variants.append(trimmed)

        if 'extended_entities' in x and 'media' in x['extended_entities']:
            entities = x['extended_entities']
            media.update([m['media_url'] for m in entities['media']])

            videos = [m['video_info'] for m in entities['media'] if m['type'] == "video"]
            for video in videos:
                urls = [n['url'] for n in video['variants'] if n['content_type'] == "video/mp4"]
                trimmed = [x.split("?")[0] for x in urls]
                media.update(trimmed)
                media_variants.append(trimmed)

        if 'in_reply_to_user_id_str' in x:
            ids.add(str(x['in_reply_to_user_id_str']))

        if "quoted_status" in x:
            ids.add(x['quoted_status']['user']['id_str'])

        ids.add(x['user']['id_str'])


    return ids, media, media_variants

def get_all_tweet_ids(*the_dirs) -> Set[Any]:
    """ For a list of directories, dfs the directory to get all files,
    and get all mentioned tweets in those files """
    tweet_ids = set()

    for a_dir in the_dirs:
        if isfile(a_dir):
            with open(a_dir, 'r') as f:
                tweet_ids.update([x.strip() for x in f.readlines()])

        elif isdir(a_dir):
            all_files = dfs_directory(*the_dirs)
            for x in all_files:
                tweet_ids.update(extract_tweet_ids_from_file(x))

    return tweet_ids

def get_user_and_media_sets(json_dir):
    """ Get all user ids and media urls """
    logging.info("Getting media urls")
    json_files = [join(json_dir, x) for x in listdir(json_dir) if splitext(x)[1] == ".json"]
    users = set()
    media = set()
    variants = []
    for f in json_files:
        tusers, tmedia, tvariants = extract_media_and_users_from_json(f)
        users.update(tusers)
        media.update(tmedia)
        variants += tvariants

    logging.info("Found {} unique media files".format(len(media)))
    logging.info("Found {} unique users".format(len(users)))

    return users, media, variants
