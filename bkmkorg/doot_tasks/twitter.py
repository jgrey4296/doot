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

import bkmkorg.twitter.mixin_passes as passes
import doot
from bkmkorg.apis.twitter import TweepyMixin, TwitterMixin
from bkmkorg.twitter.org_writer import TwitterTweet
from bkmkorg.twitter.todo_list import TweetTodoFile
from bkmkorg.twitter.tweet_graph import TwitterGraph
from doot import globber
from doot.tasker import DootTasker
from doot.task_mixins import ActionsMixin, BatchMixin, ZipperMixin
from doot.taskslib.files.downloader import DownloaderMixin

import twitter

if TYPE_CHECKING:
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.taskslib.files.backup import BackupTask

user_batch_size : Final = doot.config.on_fail(100, int).tool.doot.twitter.user_batch()

empty_match = re.match("","")


class TwitterFull(DootTasker):

    def __init__(self, name="twitter::go", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            "task_dep": ["twitter::tweets",
                         "twitter::users",
                         "twitter::components",
                         "twitter::threads",
                         "twitter::write",
                         "twitter::media",
                     ],
        })
        return task

class TwitterLibTweets(DootTasker, ActionsMixin, TwitterMixin):
    """
    (data -> temp ) download tweets from the library as jsons
    """

    def __init__(self, name="twitter::libtweets", locs=None):
        super().__init__(name, locs)
        logging.info("Setting up %s", name)
        self.twitter        = None
        self.target_ids     = set()
        self.library_ids    = set()
        self.existing_json_ids = set()
        self.output         = self.locs.lib_tweets
        self.locs.ensure("secrets", "missing_ids", "tweet_archive", "thread_library")

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
        print("---------- Getting target Tweet ids")
        target = self.locs.thread_library / ".tweets"
        if not target.exists():
            return

        count = 0
        for line in fileinput.input(files=[self.locs.thread_library / ".tweets"]):
            count += 1
            self.target_ids.add(pl.Path(line.strip()).name)

        print("Found %s library ids from %s lines" % (len(self.target_ids), count))

    def read_temp_ids(self, fpath):
        print("---------- Getting Temp Tweet ids")
        for jfile in fpath.glob('*.json'):
            data = json.loads(jfile.read_text(), strict=False)
            ids  = [x['id_str'] for x in data if bool(x['id_str'])]
            self.existing_json_ids.update(ids)

        print("Read %s temp ids" % len(self.existing_json_ids))

    def read_missing_ids(self, fpath):
        print("---------- Getting Missing Tweet ids")
        if not fpath.exists():
            return

        text = fpath.read_text().split("\n")
        ids  = [x.strip() for x in text]
        print("Read %s missing ids" % len(ids))
        self.existing_json_ids.update(ids)

    def calc_remaining_ids(self):
        print("---------- Calculating Target Tweet ids")
        print("Initial Library Ids: %s" % len(self.target_ids))
        print("Existing Json Ids: %s" % len(self.existing_json_ids))
        raw_todo_ids = self.target_ids
        remaining    = raw_todo_ids - self.existing_json_ids
        print("Remaining Target Ids: %s" % len(remaining))
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

class TwitterTweets(DootTasker, ActionsMixin, TwitterMixin):
    """
    (data -> temp ) download tweets and their thread predecessors using todo file
    """

    def __init__(self, name="twitter::tweets", locs=None):
        super().__init__(name, locs)
        logging.info("Setting up %s", name)
        self.twitter     = None
        self.library_ids = set()
        self.todos       = None
        self.output      = self.locs.tweets
        self.locs.ensure("secrets", "missing_ids", "tweet_archive", "thread_library", "current_tweets")

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
            "clean"    : [ (self.rmdirs, [self.output]) ],
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

class TwitterUserIdentities(globber.LazyGlobMixin, globber.DootEagerGlobber, BatchMixin, ActionsMixin, TwitterMixin):
    """
    (temp -> temp) download identities of user id's found in tweets
    """

    def __init__(self, name="twitter::users", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.tweets], rec=rec, exts=exts or [".json"])
        self.twitter    = None
        self.todo_users = set()
        self.lib_users  = set()
        self.output     = self.locs.users
        self.locs.ensure("secrets", "thread_library", "tweets")

    def setup_detail(self, task):
        task.update({
            "actions" : [ (self.setup_twitter, [self.locs.secrets]),
                          (self.mkdirs, [self.output]),
                          (self.load_library_users, [self.locs.thread_library / ".users"]),
                         ],
            "task_dep" : ["twitter::tweets"],
        })
        return task

    def load_library_users(self, fpath):
        if not fpath.exists():
            return
        self.lib_users.update(x.strip() for x in fpath.read_text().split("\n"))
        print("Library users file records %s ids", len(self.lib_users))

    def task_detail(self, task):
        task.update({
            "actions": [
                self.load_all_users,
                lambda: print(f"-------------------- Loaded ID strings, {len(self.todo_users)} to process"),
                (self.retrieve_users_in_batches, [self.locs.tweets]),
            ],
            "clean" : [(self.rmdirs, [self.output])],
        })
        return task

    def load_all_users(self):
        print("-------------------- Loading User Ids out of Tweet Data")
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        chunks = self.chunk(globbed)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
            data = json.loads(fpath.read_text())
            for tweet in data:
                user = tweet['user']['id_str']
                if user not in self.lib_users:
                    self.todo_users.add(user)

    def retrieve_users_in_batches(self, fpath):
        print(f"-------------------- Getting User Identities: {len(self.todo_users)}")
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

class TwitterComponentGraph(DootTasker, ActionsMixin, passes.TwGraphComponentMixin):
    """
    (temp -> temp) combine individual tweets into threads
    """

    def __init__(self, name="twitter::components", locs=None):
        super().__init__(name, locs)
        self.output      = self.locs.components
        self.tweet_graph = TwitterGraph()
        self.locs.ensure("tweets", "users")

    def setup_detail(self, task):
        task.update({
            "actions": [ (self.mkdirs, [self.output]) ],
            "task_dep" : ["twitter::tweets"],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                (self.build_graph, [self.locs.tweets]),
                (self.tw_construct_component_files, [self.locs.tweets, self.locs.users])],
            "clean" : [ (self.rmdirs, [self.output]) ],
            "task_dep": ["twitter::tweets"],
        })
        return task

    def build_graph(self, fpath):
        tweet_files = list(fpath.glob("*.json"))
        for jfile in tweet_files:
            data = json.loads(jfile.read_text())
            for tweet in data:
                self.tweet_graph.add_tweet(tweet, source=jfile)

        logging.info("Graph Built")

class TwitterThreadBuild(globber.LazyGlobMixin, globber.DootEagerGlobber, ActionsMixin, BatchMixin, passes.TwThreadBuildMixin):
    """
    (components -> threads)
    """

    def __init__(self, name="twitter::threads", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.components], rec=rec, exts=exts or [".json"])
        self.output = self.locs.threads

    def setup_detail(self, task):
        task.update({
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [ self.construct_all_threads ],
            "clean": [(self.rmdirs, [self.output])],
        })
        return task

    def construct_all_threads(self):
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        print(f"-------------------- Constructing threads for {len(globbed)} components")
        chunks = self.chunk(globbed)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
            self.tw_construct_thread(fpath)

class TwitterThreadWrite(globber.LazyGlobMixin, globber.DootEagerGlobber, passes.TwThreadWritingMixin, BatchMixin, ActionsMixin):
    """
    (threads -> build) build the org files from threads
    """

    def __init__(self, name="twitter::write", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.threads], rec=rec, exts=exts or [".json"])
        self.todos = None
        # Just Build, as construct org/html uses subdirs
        self.output = self.locs.build
        self.locs.ensure("current_tweets")

    def setup_detail(self, task):
        task.update({
            "actions": [
                (self.read_target_ids, [ self.locs.current_tweets ]),
                ],
        })
        return task

    def read_target_ids(self, fpath):
        print("---------- Getting Target Tweet ids")
        self.todos = TweetTodoFile.read(fpath)
        logging.info("Found %s source ids", len(self.todos))

    def task_detail(self, task):
        task.update({
            "actions" : [ self.make_all_orgs ],
            "clean"   : [ (self.rmdirs, [self.output / "org", self.output / "html"]) ],
        })
        return task

    def make_all_orgs(self):
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        chunks = self.chunk(globbed)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
            self.tw_construct_org_files(fpath)
            # self.tw_construct_html_files(fpath)

class TwitterDownloadMedia(globber.LazyGlobMixin, globber.DootEagerGlobber, DownloaderMixin, BatchMixin):
    """
    (threads, components -> build) read components, get media, download into the base user's _files dir
    """

    def __init__(self, name="twitter::media", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.threads], rec=rec, exts=exts or [".json"])
        self.output = self.locs.on_fail(locs.build).media()

    def setup_detail(self, task):
        task.update({

        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [ self.process_all_components ],
        })
        return task

    def process_all_components(self):
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        chunks = self.chunk(globbed)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
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
                continue

            # download
            self.download_media(download_to, media)

class TwitterMerge(globber.LazyGlobMixin, globber.DootEagerGlobber, ActionsMixin, BatchMixin):
    """
    (temp -> data) integrate threads into the library
    """

    def __init__(self, name="twitter::merge", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.orgs], rec=rec, exts=exts or [".org"])
        self.base_user_reg = re.compile(r"^(.+?)_thread_\d+$")
        self.group_reg     = re.compile(r"^[a-zA-Z]")
        self.files_dir_reg = re.compile(r"^(.+?)_files$")
        self.locs.ensure("thread_library", "media")

    def task_detail(self, task):
        task.update({
            "actions" : [ self.merge_all_threads, self.merge_all_media ]
        })
        return task

    def merge_all_threads(self):
        print("Merging Threads")
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        chunks  = self.chunk(globbed)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
            lib_path = self.build_lib_path(fpath)
            if lib_path is None:
                continue

            self.mkdirs(lib_path)
            thread_count = len(list(lib_path.glob("thread_*.org")))
            self.copy_thread(lib_path, fpath, thread_count + 1)

    def build_lib_path(self, fpath):
        lib_base  = self.locs.thread_library

        match (self.base_user_reg.match(fpath.stem) or empty_match).groups():
            case ():
                print(f"Unknown base User: {fpath}")
                return None
            case (str() as base_user):
                if re.match(r"^[a-zA-Z]", base_user):
                    group = f"group_{base_user[0]}"
                else:
                    group = "group_symbols"

                return lib_base / group / base_user
            case _:
                raise ValueError("Unexpected base value regex result")

    def copy_thread(self, dest, src, count):
        copy_target = dest / f"thread_{count}{src.suffix}"
        assert(not copy_target.exists())
        self.copy_to(copy_target, src, fn="file")

    def merge_all_media(self):
        print("Merging Media")
        for fdir in self.locs.media.iterdir():
            if fdir.is_file():
                continue
            print(f"- {fdir.stem}")
            lib_path = self.build_lib_path(fdir.parent)
            dest = lib_path / fdir.name
            if not dest.exists():
                dest.mkdir()

            for x in list(fdir.glob("*")):
                self.copy_to(dest, x)

