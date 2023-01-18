
##-- imports
from __future__ import annotations

import json
import logging as root_logger
import pathlib as pl
import re
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.files.dfs import dfs as dfs_directory
##-- end imports

logging = root_logger.getLogger(__name__)

PERMALINK_RE = re.compile(r"\[.+?/status/(\d+)\]\]")

def extract_tweet_ids_from_file(the_file:pl.Path, simple=False):
    """ Get all mentioned tweets in a file.
    Can search for regexs, or treat file as a line list of urls """
    use_regex = PERMALINK_RE
    if simple:
        use_regex = re.compile(r"/status/(\d+)")

    assert(the_file.exists())
    try:
        with open(the_file, 'r') as f:
            lines = f.readlines()
    except UnicodeDecodeError as err:
        logging.warning("File Error: %s", the_file)
        raise err

    # grep file lines for permalinks
    results = set()
    for line in lines:
        match = use_regex.search(line)
        if match is not None:
            results.add(match[1])

    return results

def extract_tweet_ids_from_json(the_file:pl.Path):
    """ Get all tweet ids from a json file of tweets """
    try:
        with open(the_file, 'r') as f:
            data = json.load(f, strict=False)
    except Exception as e:
        logging.info("File issue: %s", the_file)
        raise e

    ids = [x['id_str'] for x in data]
    return ids

def extract_media_and_users_from_json(the_file:pl.Path):
    """ Get all media urls and user ids from json file of tweets """
    try:
        with open(the_file, 'r') as f:
            data = json.load(f, strict=False)
    except Exception as e:
        logging.info("File issue: %s", the_file)
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

def get_all_tweet_ids(*the_dirs:list[pl.Path], ext=None) -> Set[str]:
    """ For a list of directories, dfs the directory to get all files,
    and get all mentioned tweets in those files """
    tweet_ids = set()

    for a_dir in the_dirs:
        if a_dir.is_file():
            with open(a_dir, 'r') as f:
                tweet_ids.update([x.strip() for x in f.readlines()])

        elif a_dir.is_dir():
            all_files = dfs_directory(a_dir, ext=ext)
            logging.info("Found %s files to extract from", len(all_files))
            for x in all_files:
                tweet_ids.update(extract_tweet_ids_from_file(x))

    return tweet_ids

def get_user_and_media_sets(json_dir:pl.Path) -> Tuple[Set[str], Set[str], List[Any]]:
    """ Get all user ids and media urls from a directory of jsons of tweets """
    logging.info("Getting media urls")
    json_files = [x for x in json_dir.iterdir() if x.suffix == ".json"]
    users = set()
    media = set()
    variants = []
    for f in json_files:
        tusers, tmedia, tvariants = extract_media_and_users_from_json(f)
        users.update(tusers)
        media.update(tmedia)
        variants += tvariants

    logging.info("Found %s unique media files", len(media))
    logging.info("Found %s unique users", len(users))

    return users, media, variants

def get_library_tweets(lib:List[pl.Path], tweet) -> Set[str]:
    library_tweet_ids = set()
    if tweet is None:
        logging.info("---------- Getting Library Tweet Details")
        logging.info("Libraries to search: %s", lib)
        library_tweet_ids = get_all_tweet_ids(*lib, ext=".org")
        logging.info("Found %s library tweets", len(library_tweet_ids))

    return library_tweet_ids
