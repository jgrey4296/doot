#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import doot
from doot.tasker import DootTasker
from doot import globber

import twitter

import bkmkorg.twitter.dfs as DFSU
import bkmkorg.twitter.tweet_retrieval as DU
import bkmkorg.twitter.extraction as EU
import bkmkorg.twitter.file_writing as FFU
from bkmkorg.twitter.api_setup import setup_twitter
from bkmkorg.twitter.data.graph import TwitterGraph
from bkmkorg.twitter.data.todo_list import TweetTodoFile

def setup_target_dict(target_dir:pl.Path, export:None|pl.Path):
    targets = {}
    targets['target_dir']           = target_dir
    targets['target_file']          = target_dir / "current.tweets"
    targets['org_dir']              = target_dir / "orgs"
    targets['tweet_dir']            = target_dir / "tweets"
    targets['combined_threads_dir'] = target_dir / "threads"
    targets['component_dir']        = target_dir / "components"
    targets['library_ids']          = target_dir / "all_ids"
    targets['users_file']           = target_dir / "users.json"
    targets['last_tweet_file']      = target_dir / "last_tweet"
    targets['download_record']      = target_dir / "downloaded.record"
    targets['lib_tweet_record']     = export or (target_dir / "lib_tweets.record")
    targets['excludes_file']        = target_dir / "excludes"

    return targets

def read_target_ids(tweet, target_file:pl.Path) -> TweetTodoFile:
    logging.info("---------- Getting Target Tweet ids")
    if tweet is None:
        todo_ids = TweetTodoFile.read(target_file)
    else:
        todo_ids = TweetTodoFile(mapping={tweet.name : ""})
        logging.info("Specific Tweet: %s", todo_ids)

    logging.info("Found %s source ids", len(todo_ids))
    return todo_ids
def run_processor(targets, all_users, todo_ids, twit):
    if not bool([x for x in targets['component_dir'].iterdir() if x.suffix == ".json"]):
        logging.info("---------- Creating Components")
        FFU.construct_component_files(targets['tweet_dir'],
                                      targets['component_dir'],
                                      twit=twit)

    if not bool([x for x in targets['combined_threads_dir'].iterdir() if x.suffix == ".json"]):
        logging.info("---------- Creating user summaries")
        FFU.construct_user_summaries(targets['component_dir'], targets['combined_threads_dir'], all_users)

    logging.info("---------- Constructing org files")
    FFU.construct_org_files(targets['combined_threads_dir'], targets['org_dir'], all_users, todo_ids)

def process()::
    # Extract all tweet id's from library
    library_tweet_ids : Set[str] = EU.get_library_tweets(args.library, args.tweet)

    if targets['lib_tweet_record'] is not None:
        logging.info("---------- Exporting lib tweets to: %s", targets['lib_tweet_record'])
        now : str = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(targets['lib_tweet_record'], 'a') as f:
            f.write(f"{now}:\n\t")
            f.write("\n\t".join(sorted(library_tweet_ids)))
            f.write("\n----------------------------------------\n")

    # read file of tweet id's to handle
    todo_ids : TweetTodoFile = read_target_ids(args.tweet, targets['target_file'])

    logging.info("-------------------- Downloading Todo Tweets")
    # Download tweets
    if not args.skiptweets:
        DU.download_tweets(twit, targets['tweet_dir'], todo_ids.ids(), lib_ids=library_tweet_ids)
    else:
        logging.info("Skipping tweet download")

    logging.info("-------------------- Extracting Details from Tweets")
    # Extract details from the tweets
    user_set, media_set, variant_list = EU.get_user_and_media_sets(targets['tweet_dir'])

    # write out video variant/duplicates
    with open(targets['target_dir'] / "video_variants.json", "w") as f:
        json.dump(variant_list, f, indent=4)

    logging.info("-------------------- Getting User Identities")
    # Get user identities
    all_users : Dict[str, Any] = DU.get_user_identities(targets['users_file'], twit, user_set)

    # --------------------
    logging.info("-------------------- Starting Assembly")
    # Now create threads
    run_processor(targets, all_users, todo_ids, twit)

    logging.info("-------------------- Finished Assembly")
    new_tweet_ids = EU.get_library_tweets([targets['org_dir']],
                                       args.tweet)

    if targets['download_record'] is not None:
        logging.info("---------- Exporting lib tweets to: %s", targets['download_record'])
        now : str = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(targets['download_record'], 'a') as f:
            f.write(f"{now}:\n\t")
            f.write("\n\t".join(sorted(new_tweet_ids)))
            f.write("\n----------------------------------------\n")

    system('say -v Moira -r 50 "Finished Twitter Download"')
    logging.info("----- Finished Twitter Automation")

class TwitterIndexer(globber.EagerFileGlobber):
    """
    (data -> temp)
    """

    def __init__(self, name="twitter::index", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.data], rec=rec, exts=exts or [".org"])

    def filter(self, fpath):
        return self.control.accept

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [],
        })
        return task

class TwitterTweets(DootTasker):
    """
    (data -> temp ) download tweets and collect them into threads
    """

    def __init__(self, name="twitter::tweets", dirs=None):
        super().__init__(name, dirs)

    def task_detail(self, task):
        task.update({
            "actions" : [],
            "targets" : [ self.build / "tweet_archive.log" ],
            "file_dep" : [ self.dirs.data / "current.tweets" ],
            "task_dep" : ["twitter::index"],
        })
        return task

class TwitterUserIdentities(globber.EagerFileGlobber):
    """
    (temp -> temp)
    """

    def __init__(self, name="twitter::users", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.temp], rec=rec, exts=exts or [".json"])

    def filter(self, fpath):
        return self.control.accept

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [],
            "task_dep" : ["twitter::tweets"],
        })
        return task

class TwitterDownloadMedia(globber.EagerFileGlobber):
    """
    (temp -> temp)
    """

    def __init__(self, name="twitter::media", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.temp], rec=rec, exts=exts or [".json"])

    def filter(self, fpath):
        return self.control.accept

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [],
            "task_dep" : ["twitter::tweets"],
        })
        return task

class TwitterThreadAssemble(globber.EagerFileGlobber):
    """
    (temp -> temp)
    """

    def __init__(self, name="twitter::assemble", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.src], rec=rec, exts=exts or [".json"])

    def filter(self, fpath):
        return self.control.accept

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [],
            "task_dep" : ["twitter:tweets"],
        })
        return task

class TwitterMediaVariants(globber.EagerFileGlobber):
    """
    (temp -> temp)
    """

    def __init__(self, name="twitter::variants", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.src], rec=rec, exts=exts or [".json"])

    def filter(self, fpath):
        return self.control.accept

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [],
            "task_dep" : ["twitter::tweets"],
        })
        return task
class TwitterThreadWrite(globber.EagerFileGlobber):
    """
    (temp -> temp)
    """

    def __init__(self, name="twitter::threads", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.temp], rec=rec, exts=exts or [".json"])

    def filter(self, fpath):
        return self.control.accept

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [],
            "task_dep" : ["twitter::assemble"],
        })
        return task

class TwitterMerge(globber.EagerFileGlobber):
    """
    (temp -> data)
    """

    def __init__(self, name="twitter::merge", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.temp], rec=rec, exts=exts or [".org"])

    def filter(self, fpath):
        return self.control.accept

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : []
            "task_dep" : ["twitter::threads"],
        })
        return task
