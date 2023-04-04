
##-- imports
from __future__ import annotations

import datetime
import json
import logging as root_logger
import pathlib as pl
import uuid
from collections import defaultdict
from shutil import copyfile, rmtree
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import networkx as nx
from doot.utils.twitter.html_writer import HtmlThreadWriter
from doot.utils.twitter.lazy_component_writer import LazyComponentWriter
from doot.utils.twitter.org_writer import OrgThreadWriter
from doot.utils.twitter.thread_obj import TwitterThreadObj
from doot.utils.twitter.todo_list import TweetTodoFile
from doot.utils.twitter.tweet_graph import TwitterGraph

##-- end imports

logging = root_logger.getLogger(__name__)

REPLY  : Final = 'in_reply_to_status_id_str'
QUOTE  : Final = 'quoted_status_id_str'
ID_STR : Final = 'id_str'

# TODO could refactor output into template files, ie: jinja.

class TwGraphComponentMixin:

    tweet_graph : TwitterGraph

    def tw_construct_component_files(self, tweet_dir:pl.Path, user_dir:pl.Path):
        """
        Create intermediate component files of tweet threads
        creates a tweet_graph of all tweets in tweet_dir,
        then writes individual connected components to output
        returns any missing ids for later download
        """
        assert(self.tweet_graph is not None)
        logging.info("---------- Getting Components")
        components : List[Set[str]]
        components, rest  = self.tweet_graph.components()
        logging.info("Creating %s component files\n\tfrom: %s\n\tto: %s", len(components), tweet_dir, self.output)
        logging.info("Non-Component Tweets: %s", len(rest))

        # Tweet Components allows lazy writing to component files
        # if enough tweets in one component have been queued
        with LazyComponentWriter(self.output, components) as id_map:
            # create separate component files
            logging.info("---------- Copying Tweets to component files")
            # Load each collection of downloaded tweets
            # Note: these are *not* components
            tweet_files = tweet_dir.glob("*.json")
            for jfile in tweet_files:
                data = json.loads(jfile.read_text(), strict=False)
                id_map.add_tweets(data)

            logging.info("---------- Copying Users to component files")
            user_files = user_dir.glob("*.json")
            for jfile in user_files:
                data = json.loads(jfile.read_text(), strict=False)
                assert(isinstance(data, dict))
                id_map.add_users(data)

        logging.info("Component Files Created")
        if bool(id_map.missing):
            logging.info("Missing: (%s) %s", len(id_map.missing), id_map.missing)

        return { "missing" : list(id_map.missing) }

class TwThreadBuildMixin:

    def tw_construct_thread(self, fpath:pl.Path):
        """ dfs on components to get order  """
        # Create final orgs, grouped by head user
        logging.info("---------- Constructing Summary for: %s", fpath)
        # read fpath
        data = json.loads(fpath.read_text(), strict=False)
        tweet_lookup = { x['id_str']: x for x in data['tweets'] }
        user_lookup  = { x['id_str']: x for x in data['users'] }
        assert(bool(data))

        thread_graph         = TwitterGraph()
        for tweet in data['tweets']:
            thread_graph.add_tweet(tweet, str(fpath))

        roots  = thread_graph.roots()
        chains, extra = thread_graph.reply_chains(roots)
        if len(chains) > 1:
            logging.warning(f"Component with more than one chain: %s", fpath)
        quotes = thread_graph.get_quotes()
        assert(bool(chains))

        main_thread = max(chains, key=lambda x: len(x))
        main_index  = chains.index(main_thread)
        sub_threads = [x for x in (chains[:main_index] + chains[main_index+1:]) if bool(x)]
        sub_threads += extra

        base_user   = self._calculate_base_user(main_thread, tweet_lookup, user_lookup) or fpath.stem

        thread_obj = TwitterThreadObj(main_thread, sub_threads, quotes, str(fpath), base_user)

        # Then write the thread description out
        # uses the same name as its component
        out_file = self.output / fpath.name.replace("component", "thread")
        out_file.write_text(json.dumps(thread_obj.dump(), indent=4))

    def _calculate_base_user(self, main_thread, tweet_lookup:dict, user_lookup:dict):
        user_counts = defaultdict(lambda: 0)
        try:
            for tweet_id in main_thread:
                tweet   = tweet_lookup.get(tweet_id, {})
                user_id = tweet.get("user", {}).get("id_str", None)
                user    = user_lookup.get(user_id, {}).get("screen_name", None)
                if user:
                    user_counts[user] += 1
            return max(user_counts, key=lambda x: user_counts[x])
        except Exception as err:
            return None

class TwThreadWritingMixin:

    def tw_construct_org_files(self, fpath):
        logging.info("Constructing org file from: %s \n\tto: %s", fpath, self.output)
        thread = json.loads(fpath.read_text())
        data   = json.loads(pl.Path(thread['component']).read_text())
        tweets = data['tweets']
        users  = data['users']
        tags   = self.todos.tags_mapping

        thread_writer = OrgThreadWriter.build(thread, tweets, users, tags)
        thread_str = str(thread_writer)

        base_dir    = self.output / "org"
        count       = 0
        target_file =  f"{thread_writer.user}_thread_{count}.org"
        actual_file = base_dir / target_file
        while actual_file.exists():
            count += 1
            target_file =  f"{thread_writer.user}_thread_{count}.org"
            actual_file = base_dir / target_file

        actual_file.write_text(thread_str)

    def tw_construct_html_files(self, fpath):
        logging.info("Constructing html file from: %s \n\tto: %s", fpath, self.output)
        thread = json.loads(fpath.read_text())
        data   = json.loads(pl.Path(thread['component']).read_text())
        tweets = data['tweets']
        users  = data['users']
        tags   = self.todos.tags_mapping

        thread_writer = HtmlThreadWriter.build(thread, tweets, users, tags)
        thread_str = str(thread_writer)

        base_dir    = self.output / "org"
        count       = 0
        target_file =  f"{thread_writer.user}_thread_{count}.html"
        actual_file = base_dir / target_file
        while actual_file.exists():
            count += 1
            target_file =  f"{thread_writer.user}_thread_{count}.html"
            actual_file = base_dir / target_file

        actual_file.write_text(thread_str)
