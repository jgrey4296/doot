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
from doot.tasker import ActionsMixin, BatchMixin, DootTasker, ZipperMixin
from doot.taskslib.files.downloader import DownloaderMixin
from doot.toml_access import TomlAccess

import twitter

if TYPE_CHECKING:
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

user_batch_size : Final = doot.config.on_fail(100, int).tool.doot.twitter.user_batch()

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
                     ],
        })
        return task

class TwitterAccess(DootTasker, TwitterMixin): # TweepyMixin):

    def __init__(self, name="twitter::access", locs=None):
        super().__init__(name, locs)
        self.twitter = None
        assert(self.locs.secrets)

    def task_detail(self, task):
        task.update({
            "actions": [(self.setup_twitter, [self.locs.secrets]),
                        self.pause,
                        ],
            "verbosity": 2,
        })
        return task

    def pause(self):
        print("Pausing")
        breakpoint()
        pass

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
        assert(self.locs.secrets)
        assert(self.locs.missing_ids)
        assert(self.locs.tweet_archive)
        assert(self.locs.tweet_library)

    def task_detail(self, task):
        task.update({
            "actions"  : [ (self.mkdirs, [self.output]),
                           (self.setup_twitter, [self.locs.secrets]),
                           self.read_target_ids,
                           (self.read_temp_ids, [self.output]),
                           self.calc_missing_ids,
                           (self.read_missing_ids, [ self.locs.missing_ids ]),
                           (self.tw_download_tweets, [self.output, self.locs.missing_ids]),
                           (self.write_log, [self.locs.tweet_archive]),
                          ],
        })
        return task

    def read_target_ids(self):
        logging.info("---------- Getting target Tweet ids")
        for line in fileinput.input(files=[self.locs.tweet_library / ".tweets"]):
            self.target_ids.add(pl.Path(line).name)
        logging.info("Found %s library ids", len(self.target_ids))

    def read_temp_ids(self, fpath):
        for jfile in fpath.glob('*.json'):
            data = json.loads(jfile.read_text(), strict=False)
            ids  = [x['id_str'] for x in data]
            self.existing_json_ids.update(ids)

    def read_missing_ids(self, fpath):
        text = fpath.read_text().split("\n")
        self.existing_json_ids.update([x.strip() for x in text])

    def calc_missing_ids(self):
        raw_todo_ids = self.target_ids
        remaining = raw_todo_ids - self.existing_json_ids
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
        assert(self.locs.secrets)
        assert(self.locs.missing_ids)
        assert(self.locs.tweet_archive)
        assert(self.locs.tweet_library)
        assert(self.locs.current_tweets)

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

        for line in fileinput.input(files=[self.locs.tweet_library / ".tweets"]):
            self.library_ids.add(pl.Path(line).name)
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
        assert(self.locs.secrets)
        assert(self.locs.tweet_library)
        assert(self.locs.tweets)

    def filter(self, fpath):
        return self.control.accept

    def setup_detail(self, task):
        task.update({
            "actions" : [ (self.setup_twitter, [self.locs.secrets]),
                          (self.mkdirs, [self.output]),
                          (self.load_library_users, [self.locs.tweet_library / ".users"]),
                         ],
            "task_dep" : ["twitter::tweets"],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions": [
                lambda: print(f"-------------------- Loaded ID strings, {len(self.todo_users)} to process"),
                (self.retrieve_users_in_batches, [self.locs.tweets]),
            ],
            "clean" : [(self.rmdirs, [self.output])],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.extract_users_from_jsons, [fpath]) ],
        })
        return task

    def load_library_users(self, fpath):
        if not fpath.exists():
            return
        self.lib_users.update(x.strip() for x in fpath.read_text().split("\n"))
        print("Library users file records %s ids", len(self.lib_users))

    def extract_users_from_jsons(self, fpath):
        print("-------------------- Loading User Ids out of Tweet Data")
        jsons   = self.glob_target(fpath)
        self.run_batches(*jsons, fn=self.batch_load)

    def batch_load(self, fpath):
        print("...")
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
        print("...")
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
        assert(self.locs.tweets)
        assert(self.locs.users)

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
            "clean": [(self.rmdirs, [self.output])],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions": [(self.construct_threads, [fpath])],
        })
        return task

    def construct_threads(self, fpath):
        globbed = self.glob_target(fpath)
        print(f"-------------------- Constructing threads for {len(globbed)} components")
        self.run_batches(*globbed, fn=self.tw_construct_thread)

class TwitterThreadWrite(globber.LazyGlobMixin, globber.DootEagerGlobber, passes.TwThreadWritingMixin, BatchMixin, ActionsMixin):
    """
    (threads -> build) build the org files from threads
    """

    def __init__(self, name="twitter::write", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.threads], rec=rec, exts=exts or [".json"])
        self.todos = None
        # Just Build, as construct org/html uses subdirs
        self.output = self.locs.build
        assert(self.locs.current_tweets)

    def setup_detail(self, task):
        task.update({
            "actions": [
                (self.read_target_ids, [ self.locs.current_tweets ]),
                ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "clean" : [ (self.rmdirs, [self.output / "org", self.output / "html"]) ],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions": [
                (self.make_orgs, [fpath]),
                #(self.make_htmls, [fpath])
            ],
        })
        return task

    def read_target_ids(self, fpath):
        print("---------- Getting Target Tweet ids")
        self.todos = TweetTodoFile.read(fpath)
        logging.info("Found %s source ids", len(self.todos))

    def make_orgs(self, fpath):
        print("---------- Building Orgs from Threads")
        globbed = list(fpath.glob("*.json"))
        self.run_batches(*globbed, fn=self.tw_construct_org_files)

    def make_htmls(self, fpath):
        print("---------- Building Orgs from Threads")
        globbed = list(fpath.glob("*.json"))
        self.run_batches(*globbed, fn=self.tw_construct_html_files)

class TwitterDownloadMedia(globber.LazyGlobMixin, globber.DootEagerGlobber, DownloaderMixin):
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

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                (self.process_components, [fpath]),
            ],
        })
        return task

    def process_components(self, fpath):
        globbed = fpath.glob("*.json")
        for jfile in globbed:
            data         = json.loads(jfile.read_text())
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

class TwitterMerge(globber.DootEagerGlobber, ActionsMixin):
    """
    (temp -> data) integrate threads into the library
    """

    def __init__(self, name="twitter::merge", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.orgs], rec=rec, exts=exts or [".org"])
        self.base_user_reg = re.compile(r"^(.+?)_thread_\d+$")
        self.group_reg     = re.compile(r"^[a-zA-Z]")
        self.files_dir_reg = re.compile(r"^(.+?)_files$")
        assert(self.locs.tweet_library)
        assert(self.locs.media)

    def task_detail(self, task):
        task.update({
            "actions": [
                (self.copy_media, [ self.locs.tweet_library, self.locs.media ]),
            ]
        })
        return task

    def subtask_detail(self, task, fpath):
        lib_base  = self.locs.tweet_library
        base_user = self.base_user_reg.match(fpath.stem)[1]
        if re.match(r"^[a-zA-Z]", base_user):
            group = f"group_{base_user[0]}"
        else:
            group = "group_symbols"
        task.update({
            "actions" : [
                (self.mkdirs, [lib_base / group / base_user ]),
                (self.count_lib_threads, [lib_base / group / base_user ]),
                (self.copy_thread, [lib_base / group / base_user, fpath]),
            ],
        })
        return task

    def copy_media(self, lib, media):
        for fdir in media.iterdir():
            if fdir.is_file():
                continue

            parent = self.files_dir_reg.match(fdir.stem)[1]

            if self.group_reg.match(fdir.stem):
                group = f"group_{fdir.stem[0]}"
            else:
                group = "group_symbols"

            dest = lib / group / parent / fdir.name
            if not dest.exists():
                # print(f"Would Make: {dest}")
                dest.mkdir()

            for x in list(fdir.glob("*")):
                # print(f"Would Copy: {x} -> {dest}")
                self.copy_to(dest, x)

    def count_lib_threads(self, fpath):
        return { "count" : len(list(fpath.glob("thread_*.org"))) }

    def copy_thread(self, dest, src, task):
        count = task.values['count'] + 1
        copy_target = dest / f"thread_{count}{src.suffix}"
        assert(not copy_target.exists())
        # print(f"Would Copy: {copy_target}")
        self.copy_to(copy_target, src, fn="file")

class TwitterArchive(globber.DootEagerGlobber, ActionsMixin, ZipperMixin):
    """
    Zip json data for users

    Get Threads -> components,
    combine,
    add to archive.zip in base user's library directory
    """

    def __init__(self, name="twitter::zip", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.threads], rec=rec, exts=exts or [".json"])
        self.group_reg     = re.compile(r"^[a-zA-Z]")
        self.output         = None
        self.thread_data    = None
        self.component_data = None
        assert(self.locs.tweet_library)

    def subtask_detail(self, task, fpath):
        task.update({
            "actions": [
                (self.load_thread, [fpath]),
                self.load_component,
                self.add_to_user_archive,
            ],
        })
        return task

    def load_thread(self, fpath):
        self.thread_data = json.loads(fpath.load_text())
        return { "component": self.thread_data['component'],
                 "base_user": self.thread_data['base_user'],
                }

    def load_component(self, task):
        self.component_data = json.loads(pl.Path(task.values['component']))

    def add_to_user_archive(self, task):
        group = "group_symbols"
        if re.match(r"^[a-zA-Z]", task.values['base_user']):
            group = f"group_{base_user[0]}"

        target_path = self.locs.tweet_library / group / task.values['base_user'] / "archive.zip"
        if not target_path.exists():
            self.zip_create(target_path)

        as_json = json.dumps({"thread": self.thread_data, "component": self.component_data})
        json_name = pl.Path(task.values['component']).name
        self.zip_add_str(json_name, as_json)
