#!/usr/bin/env python3
"""
Tasks for archiving twitter threads
"""
##-- imports
from __future__ import annotations

import abc
import datetime
import fileinput
import json
import logging as logmod
import pathlib as pl
import re
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
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot.utils.twitter.mixin_passes as passes
import doot
from doot.mixins.apis.twitter import TweepyMixin, TwitterMixin
from doot.utils.twitter.org_writer import TwitterTweet
from doot.utils.twitter.todo_list import TweetTodoFile
from doot.utils.twitter.tweet_graph import TwitterGraph
from doot import globber
from doot.mixins.commander import CommanderMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.batch import BatchMixin
from doot.mixins.zipper import ZipperMixin
from doot.mixins.downloader import DownloaderMixin
from doot.tasker import DootTasker
from doot.tasks.files.backup import BackupTask

import twitter

user_batch_size : Final = doot.config.on_fail(100, int).twitter.user_batch()

empty_match = re.match("","")

class TwitterFull(DootTasker, FilerMixin):
    """
    run the combined pipeline
    """

    def __init__(self, name="twitter::go", locs=None):
        super().__init__(name, locs)
        self.locs.ensure("temp", "build", task=name)

    def task_detail(self, task):
        task.update({
            "task_dep": ["twitter::1.tweets",
                         "twitter::2.users",
                         "twitter::3.components",
                         "twitter::4.threads",
                         "twitter::5.write",
                         "twitter::6.media",
                         "twitter::7.merge",
                     ],
            "clean" : [ (self.rmdirs, [ self.locs.temp, self.locs.build ]) ]
        })
        return task

class TwitterLibTweets(DootTasker, TwitterMixin, FilerMixin, CommanderMixin):
    """
    (data -> temp ) download tweets from the library as jsons
    """

    def __init__(self, name="twitter::libtweets", locs=None):
        super().__init__(name, locs)
        self.twitter        = None
        self.target_ids     = set()
        self.library_ids    = set()
        self.existing_json_ids = set()
        self.output         = self.locs.lib_tweets
        self.locs.ensure("secrets", "missing_ids", "tweet_archive", "thread_library", task=name)

    def task_detail(self, task):
        task.update({
            "actions"  : [ (self.mkdirs, [self.output]),
                           (self.setup_twitter, [self.locs.secrets]),
                           self.read_target_ids,
                           (self.read_temp_ids, [self.output]),
                           (self.read_missing_ids, [ self.locs.missing_ids ]),
                           self.calc_remaining_ids,
                           (self.tw_download_tweets, [self.output, self.locs.missing_ids]),
                           (self.write_log, [self.locs.tweet_archive]),
                          ],
        })
        return task

    def read_target_ids(self):
        logging.info("---------- Getting target Tweet ids")
        target = self.locs.thread_library / ".tweets"
        if not target.exists():
            return

        count = 0
        for line in fileinput.input(files=[self.locs.thread_library / ".tweets"]):
            count += 1
            self.target_ids.add(pl.Path(line.strip()).name)

        logging.info("Found %s library ids from %s lines" % (len(self.target_ids), count))

    def read_temp_ids(self, fpath):
        logging.info("---------- Getting Temp Tweet ids")
        for jfile in fpath.glob('*.json'):
            data = json.loads(jfile.read_text(), strict=False)
            ids  = [x['id_str'] for x in data if bool(x['id_str'])]
            self.existing_json_ids.update(ids)

        logging.info("Read %s temp ids" % len(self.existing_json_ids))

    def read_missing_ids(self, fpath):
        logging.info("---------- Getting Missing Tweet ids")
        if not fpath.exists():
            return

        text = fpath.read_text().split("\n")
        ids  = [x.strip() for x in text]
        logging.info("Read %s missing ids" % len(ids))
        self.existing_json_ids.update(ids)

    def calc_remaining_ids(self):
        logging.info("---------- Calculating Target Tweet ids")
        logging.info("Initial Library Ids: %s" % len(self.target_ids))
        logging.info("Existing Json Ids: %s" % len(self.existing_json_ids))
        raw_todo_ids = self.target_ids
        remaining    = raw_todo_ids - self.existing_json_ids
        logging.info("Remaining Target Ids: %s" % len(remaining))
        return { "target_ids": list(remaining) }

    def write_log(self, fpath, task):
        newly_downloaded = task.values['downloaded']
        if not bool(newly_downloaded):
            return

        now = datetime.datetime.now().strftime("%d/%m/%y")
        with open(fpath, 'a') as f:
            f.write("\n--------------------")
            f.write(f" Downloaded on: {now} ")
            f.write("--------------------\n")
            f.write("\n".join(newly_downloaded))

class TwitterTweets(DootTasker, TwitterMixin, FilerMixin):
    """
    (data -> temp ) download tweets and their thread predecessors using todo file
    """

    def __init__(self, name="twitter::1.tweets", locs=None):
        super().__init__(name, locs)
        self.twitter     = None
        self.library_ids = set()
        self.todos       = None
        self.output      = self.locs.tweets
        self.locs.ensure("secrets", "missing_ids", "tweet_archive", "thread_library", "current_tweets", task=name)

    def set_params(self):
        return [
            {"name": "tweet", "type": str, "short": "t", "default": None},
            {"name": "no-lib", "type": bool, "short": "l", "default": False}
        ]

    def setup_detail(self, task):
        task.update({
            "actions"  : [ (self.mkdirs, [self.output]),
                          (self.setup_twitter, [self.locs.secrets]),
                          self.read_library_ids,
                          (self.read_temp_ids, [self.output]),
                          (self.read_missing_ids, [ self.locs.missing_ids ]),
                     ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.read_target_ids,
                           self.calc_missing_ids,
                           (self.tw_download_tweets, [self.output, self.locs.missing_ids]),
                           (self.write_log, [self.locs.tweet_archive]),
                          ],
            "targets"  : [ self.locs.tweet_archive ],
            "file_dep" : [ self.locs.current_tweets ],
        })
        return task

    def read_target_ids(self, dependencies):
        logging.info("---------- Getting Target Tweet ids")
        if self.args['tweet'] is not None:
            self.todos = TweetTodoFile()
            self.todos.mapping[self.args['tweet']] = ","
            return
        self.todos = TweetTodoFile.read(pl.Path(dependencies[0]))
        logging.info("Found %s source ids", len(self.todos))

    def read_library_ids(self):
        logging.info("---------- Getting Library Tweet ids")
        if self.args['no-lib']:
            return

        for line in fileinput.input(files=[self.locs.thread_library / ".tweets"]):
            self.library_ids.add(pl.Path(line.strip()).name)
        logging.info("Found %s library ids", len(self.library_ids))

    def read_temp_ids(self, fpath):
        if self.args['no-lib']:
            return

        for jfile in fpath.glob('*.json'):
            data = json.loads(jfile.read_text(), strict=False)
            ids  = [x['id_str'] for x in data]
            self.library_ids.update(ids)

    def read_missing_ids(self, fpath):
        if not fpath.exists() or self.args['no-lib']:
            return

        text = fpath.read_text().split("\n")
        self.library_ids.update([x.strip() for x in text])

    def calc_missing_ids(self):
        raw_todo_ids = self.todos.ids()
        remaining = raw_todo_ids - self.library_ids
        logging.info("Calculated %s missing tweet ids", len(remaining))
        return { "target_ids": list(remaining) }

    def write_log(self, fpath, task):
        newly_downloaded = task.values['downloaded']
        if not bool(newly_downloaded):
            return

        now = datetime.datetime.now().strftime("%d/%m/%y")
        with open(fpath, 'a') as f:
            f.write("\n--------------------")
            f.write(f" Downloaded on: {now} ")
            f.write("--------------------\n")
            f.write("\n".join(newly_downloaded))

class TwitterUserIdentities(DelayedMixin, globber.DootEagerGlobber, BatchMixin, TwitterMixin, FilerMixin):
    """
    (temp -> temp) download identities of user id's found in tweets
    """

    def __init__(self, name="twitter::2.users", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.tweets], rec=rec, exts=exts or [".json"])
        self.twitter    = None
        self.todo_users = set()
        self.lib_users  = set()
        self.output     = self.locs.users
        self.locs.ensure("secrets", "thread_library", "tweets", task=name)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                (self.mkdirs, [self.output]),
                (self.setup_twitter, [self.locs.secrets]),
                (self.load_library_users, [self.locs.thread_library / ".users"]),
            ],
            # "task_dep" : ["twitter::1.tweets"],
        })
        return task

    def load_library_users(self, fpath):
        if not fpath.exists():
            return
        self.lib_users.update(x.strip() for x in fpath.read_text().split("\n"))
        logging.info("Library users file records %s ids", len(self.lib_users))

    def task_detail(self, task):
        task.update({
            "actions": [
                (self.log, [f"-------------------- Loaded ID strings, {len(self.todo_users)} to process"], {"level": logmod.INFO}),
                (self.retrieve_users_in_batches, [self.locs.tweets]),
            ],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.load_users, [fpath]) ],
        })
        return task

    def load_users(self, fpath):
        logging.info("Loading Users in: %s", fpath)
        data = json.loads(fpath.read_text())
        for tweet in data:
            user = tweet['user']['id_str']
            if user not in self.lib_users:
                self.todo_users.add(user)

    def retrieve_users_in_batches(self, fpath):
        logging.info(f"-------------------- Getting User Identities: {len(self.todo_users)}")
        user_queue  = self.chunk(sorted(self.todo_users), user_batch_size)
        self.run_batches(*user_queue, fn=self.batch_retrieve)

    def batch_retrieve(self, data):
        result      = self.twitter.UsersLookup(user_id=data)
        new_users   = [json.loads(x.AsJsonString()) for x in result]
        user_dict   = {x['id_str'] : x for x in new_users}
        users_file  = self.output / f"users_{data[0]}.json"
        if users_file.exists():
            user_dict.update(json.loads(users_file.read_text()))
        users_file.write_text(json.dumps(user_dict, indent=4))

class TwitterComponentGraph(DootTasker, passes.TwGraphComponentMixin, FilerMixin):
    """
    (temp -> temp) combine individual tweets into threads
    """

    def __init__(self, name="twitter::3.components", locs=None):
        super().__init__(name, locs)
        self.output      = self.locs.components
        self.tweet_graph = TwitterGraph()
        self.locs.ensure("tweets", "users", task=name)

    def setup_detail(self, task):
        task.update({
            "actions": [ (self.mkdirs, [self.output]) ],
            # "task_dep" : ["twitter::1.tweets"],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                (self.build_graph, [self.locs.tweets]),
                (self.tw_construct_component_files, [self.locs.tweets, self.locs.users])],
            # "task_dep": ["twitter::1.tweets"],
        })
        return task

    def build_graph(self, fpath):
        logging.info("-- Building Component Graph")
        tweet_files = list(fpath.glob("*.json"))
        for jfile in tweet_files:
            data = json.loads(jfile.read_text())
            for tweet in data:
                self.tweet_graph.add_tweet(tweet, source=jfile)

        logging.info("Graph Built")

class TwitterThreadBuild(DelayedMixin, globber.DootEagerGlobber, BatchMixin, passes.TwThreadBuildMixin, FilerMixin):
    """
    (components -> threads)
    """

    def __init__(self, name="twitter::4.threads", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.components], rec=rec, exts=exts or [".json"])
        self.output = self.locs.threads

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.tw_construct_thread, [fpath]) ],
        })
        return task

class TwitterThreadWrite(DelayedMixin, globber.DootEagerGlobber, passes.TwThreadWritingMixin, BatchMixin, FilerMixin):
    """
    (threads -> build) build the org files from threads
    """

    def __init__(self, name="twitter::5.write", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.threads], rec=rec, exts=exts or [".json"])
        self.todos = None
        # Just Build, as construct org/html uses subdirs
        self.output = self.locs.build
        self.locs.ensure("current_tweets", task=name)

    def setup_detail(self, task):
        task.update({
            "actions": [
                (self.read_target_ids, [ self.locs.current_tweets ]),
                ],
        })
        return task

    def read_target_ids(self, fpath):
        logging.info("---------- Getting Target Tweet ids")
        self.todos = TweetTodoFile.read(fpath)
        logging.info("Found %s source ids", len(self.todos))

    def task_detail(self, task):
        task.update({})
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.tw_construct_org_files, [fpath]) ],
        })
        return task

class TwitterDownloadMedia(DelayedMixin, globber.DootEagerGlobber, DownloaderMixin, BatchMixin, FilerMixin):
    """
    download media associated with threads
    """

    def __init__(self, name="twitter::6.media", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.threads], rec=rec, exts=exts or [".json"])
        self.output = self.locs.on_fail(locs.build).media()

    def setup_detail(self, task):
        task.update({})
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.process_component, [fpath]) ],
        })
        return task

    def process_component(self, fpath):
        data         = json.loads(fpath.read_text())
        component    = json.loads(pl.Path(data['component']).read_text())
        tweets       = component['tweets']
        base_user    = data['base_user']
        download_to  = self.output / f"{base_user}_files"

        # extract media
        media = set()
        for tweet in tweets:
            for lst in TwitterTweet.get_tweet_media(tweet).values():
                media.update({x.get("url", None) for x in lst})

        if not bool(media):
            return

        # download
        self.download_media(download_to, media)

class TwitterMerge(DelayedMixin, globber.DootEagerGlobber, BatchMixin, FilerMixin):
    """
    (temp -> data) integrate threads into the library
    """

    def __init__(self, name="twitter::7.merge", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.orgs], rec=rec, exts=exts or [".org"])
        self.base_user_reg = re.compile(r"^(.+?)_thread_\d+$")
        self.group_reg     = re.compile(r"^[a-zA-Z]")
        self.files_dir_reg = re.compile(r"^(.+?)_files$")
        self.locs.ensure("thread_library", "media", task=name)

    def task_detail(self, task):
        task.update({
            "actions" : [ self.merge_all_media ],
            "task_dep" : [ ],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.merge_thread, [fpath])  ],
        })
        return task

    def merge_thread(self, fpath):
        lib_path = self.build_lib_path(fpath)
        if lib_path is None:
            return

        logging.info("-- Merging: %s", fpath)
        self.mkdirs(lib_path)
        thread_count = len(list(lib_path.glob("thread_*.org")))
        self.copy_thread(lib_path, fpath, thread_count + 1)

    def build_lib_path(self, fpath):
        lib_base  = self.locs.thread_library
        match fpath:
            case str() if fpath[0].lower().isalpha():
                group = f"group_{fpath[0].lower()}"
                return lib_base / group / fpath
            case str():
                return lib_base / "group_symbols" / fpath
            case pl.Path():
                pass
            case _:
                raise TypeError(f"Unrecognized lib path arg: {fpath}")

        match (self.base_user_reg.match(fpath.stem) or empty_match).groups():
            case ():
                raise ValueError(f"Couldn't match path for library: {fpath}")
            case (str() as base_user) | (str() as base_user, ) if base_user[0].isalpha():
                group = f"group_{base_user[0]}"
                return lib_base / group / base_user
            case (str() as base_user) | (str() as base_user, ):
                group = "group_symbols"
                return lib_base / group / base_user
            case _ as val:
                raise ValueError(f"Unexpected base value regex result: {val}")

    def copy_thread(self, dest, src, count):
        copy_target = dest / f"thread_{count}{src.suffix}"
        assert(not copy_target.exists())
        self.copy_to(copy_target, src, fn="file")
        self.move_to(src.with_suffix(".org_copied"), src, fn="file")

    def merge_all_media(self):
        logging.info("Merging Media")
        for fdir in self.locs.media.iterdir():
            if fdir.is_file() or fdir == self.locs.media:
                continue

            lib_path = self.build_lib_path(fdir.name.replace("_files", ""))
            dest     = lib_path / fdir.name
            logging.info(f"- {fdir.stem}")
            if not dest.exists():
                dest.mkdir(parents=True)

            for x in list(fdir.glob("*")):
                self.copy_to(dest, x)

class TwitterArchive(DelayedMixin, globber.DootEagerGlobber, CommanderMixin, BatchMixin, ZipperMixin):
    """
    Zip json data for users

    Get Threads -> components,
    combine,
    add to archive.zip in base user's library directory
    """

    def __init__(self, name="twitter::zip", locs=None, roots=None, rec=True, exts=None):
        super().__init__(name, locs, roots or [locs.threads], rec=rec, exts=exts or [".json"])
        self.group_reg      = re.compile(r"^[a-zA-Z]")
        self.output         = None
        self.thread_data    = None
        self.component_data = None
        self.locs.ensure("thread_library", "threads", task=name)

    def filter(self, fpath):
        return fpath.is_file()

    def subtask_detail(self, task, fpath):
        task.update({
            "actions": [ (self.add_to_archive, [fpath]) ],
        })
        return task

    def add_to_archive(self, fpath):
        self.thread_data    = json.loads(fpath.read_text())
        self.component_data = json.loads(pl.Path(self.thread_data['component']).read_text())
        component           = self.thread_data['component']
        base_user           = self.thread_data['base_user']
        target_path         = self.calc_target_path(base_user)
        self.add_to_user_archive(target_path, base_user, component)

    def calc_target_path(self, base_user):
        group = "group_symbols"
        if re.match(r"^[a-zA-Z]", base_user):
            group = f"group_{base_user[0]}"

        target_path = self.locs.thread_library / group / base_user / "archive.zip"
        return target_path

    def add_to_user_archive(self, target_path, base_user, component):
        logging.info("- Adding to: %s", base_user)
        as_json = json.dumps({"thread": self.thread_data, "component": self.component_data})
        json_name = pl.Path(component).name

        self.zip_add_str(target_path, json_name, as_json)
