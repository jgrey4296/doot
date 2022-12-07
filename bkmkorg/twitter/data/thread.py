#!/usr/bin/env python3
# pylint: disable=missing-function-docstring
# pylint: disable=line-too-long
# pylint: disable=missing-class-docstring
# pylint: disable=too-many-arguments
"""
A Collection of dataclasses which reduce to json
"""
##-- imports
from __future__ import annotations

import datetime
import json
import logging as root_logger
import pathlib as pl
from collections import defaultdict
from os.path import split
from dataclasses import InitVar, dataclass, field
from itertools import cycle
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from uuid import uuid1

import networkx as nx
from bkmkorg.files.download import download_media
from bkmkorg.twitter.tweet_retrieval import download_tweets
from bkmkorg.org.string_builder import OrgStrBuilder
##-- end imports

logging = root_logger.getLogger(__name__)

@dataclass
class TwitterOrg:
    """ Create an Org File from twitter user summary """

    summary_path : pl.Path
    dir_s        : pl.Path

    tag_lookup   : 'TweetTodoFile'
    user_lookup  : Dict[str, Any]


    org_suffix    : str = field(default=".org")
    files_pattern : str = field(default="{}_files")


    _summary : Any                               = field(init=False, default=None)
    _id_s    : str                               = field(init=False, default=None)
    _output  : List[Union[str, 'OrgStrBuilder']] = field(init=False, default_factory=list)
    _media   : Set[str]                          = field(init=False, default_factory=set)
    _used    : Set[str]                          = field(init=False, default_factory=set)

    def __post_init__(self):
        with open(self.summary_path, 'r') as f:
            self._summary = json.load(f, strict=False)

        self._id_s = self._summary['user']['screen_name']

        self.build_header()

    @property
    def path(self):
        return (self.dir_s / self._id_s).with_suffix(self.org_suffix)

    @property
    def relative_files_path(self):
        return self.files_pattern.format(self._id_s)

    @property
    def absolute_files_path(self):
        return self.dir_s / self.relative_files_path

    @property
    def tweets(self):
        return self._summary['tweets']

    def __bool__(self):
        return bool(self.tweets)

    def write(self):
        with open(self.path, 'w') as f:
            f.write("\n".join([str(x) for x in self._output]))

    def build_header(self):
        output = OrgStrBuilder()
        output.heading(1, "{}'s Threads".format(self._summary['user']['screen_name']))
        with output.drawer("PROPERTIES") as dr:
            if 'name' in self._summary['user']:
                dr.add("NAME", self._summary['user']['name'])
            if 'followers_count' in self._summary['user']:
                dr.add("FOLLOWERS", self._summary['user']['followers_count'])
            if 'description' in self._summary['user']:
                dr.add("DESCRIPTION", self._summary['user']['description'].replace("\n", " "))
            if 'location' in self._summary['user']:
                dr.add("LOCATION", self._summary['user']['location'])
            if 'url' in self._summary['user']:
                dr.add("URL", "[[{}]]".format(self._summary['user']['url']))
            dr.add("TWITTER-BUFFER", "t")


        self._output.append(output)


    def build_threads(self):
        for thread in self._summary['threads']:
            thread_obj = TwitterThread.build(thread,
                                             self.relative_files_path,
                                             self.user_lookup,
                                             self.tweets,
                                             self.tag_lookup)

            if thread_obj is not None:
                self._output.append(thread_obj)
                self._media.update(thread_obj.media)

    def download_media(self):
        """ copy media to correct output files dir """
        if not bool(self._media):
            return

        if not self.absolute_files_path.exists() and bool(self._media):
            self.absolute_files_path.mkdir()

        if bool(self._media):
            download_media(self.absolute_files_path, self._media)

@dataclass
class TwitterThread:
    """ Given a thread object, build a string representation for it
    redirecting absolute media paths to relative
    """

    redirect_url  : str
    date          : datetime.datetime
    tags          : Set[str]
    main          : List['TwitterTweet']       = field(default_factory=list)
    conversations : List[List['TwitterTweet']] = field(default_factory=list)
    remainder     : List['TwitterTweet']       = field(default_factory=list)
    uses          : Set[str]                   = field(default_factory=set)
    links         : Set[str]                   = field(default_factory=set)
    media         : Set[str]                   = field(default_factory=set)

    date_re       : str = r"%a %b %d %H:%M:%S +0000 %Y"
    tag_pattern   : str = ":{}:"
    tag_sep       : str = ":"
    tag_col       : int = 80

    @staticmethod
    def build(thread, redirect_url, all_users, tweets, source_ids) -> 'TwitterThread':
        logging.info("Creating thread")
        assert(isinstance(thread, dict))
        assert(isinstance(all_users, dict))

        thread_tweet_ids = thread['total']

        if not bool(thread_tweet_ids):
            return None

        existing = [x for x in thread['main_thread'] if x in tweets]
        if not bool(existing):
            logging.warning("Invalid Thread provided")
            obj = TwitterThread(redirect_url, "UNKNOWN", set())
            for x in thread['main_thread']:
                obj.append(x)
            return obj


        thread_date = tweets[existing[0]]['created_at']
        date = TwitterThread.parse_date(thread_date)
        tags = {y.strip() for x in thread_tweet_ids for y in source_ids.mapping[x].split(",") if bool(y)}

        obj = TwitterThread(redirect_url, date, tags)

        # add tweets of main thread
        for x in thread['main_thread']:
            if x not in tweets:
                continue
            obj.add_use(x)
            tweet_obj = TwitterTweet.build(tweets[x], all_users, redirect_url, tweets)
            obj.main.append(tweet_obj)
            obj.media.update(tweet_obj.media)
            obj.links.update(tweet_obj.links)

        # Add sub conversations
        for conv in thread['rest']:
            conv_list = []
            for x in conv:
                obj.add_use(x)
                tweet_obj = TwitterTweet.build(tweets[x], all_users, redirect_url, tweets, level=5)
                conv_list.append(tweet_obj)
                obj.media.update(tweet_obj.media)
                obj.links.update(tweet_obj.links)

            obj.conversations.append(conv_list)

        # Then add unused tweets
        unused_keys = obj.uses.difference(thread['total'])
        for x in unused_keys:
            obj.add_use(x)
            tweet_obj = TwitterTweet.build(tweets[x], all_users, redirect_url, tweets)
            obj.remainder.append(tweet_obj)
            obj.media.update(tweet_obj.media)
            obj.links.update(tweet_obj.links)

        assert(not bool(obj.uses.difference(thread['total'])))
        return obj

    def add_use(self, value):
        """
        Record a use of a tweet id
        """
        self.uses.add(value)


    @staticmethod
    def retarget_url(url, new_target_dir):
        logging.debug("Retargeting URL: %s to %s", split(url)[1], new_target_dir)
        return f"{new_target_dir}/{split(url)[1]}"

    @staticmethod
    def parse_date( a_str) -> 'datetime':
        """ Parse a twitter 'created_at' string to a date """
        return datetime.datetime.strptime(a_str, TwitterThread.date_re)


    def __str__(self):
        output = OrgStrBuilder()

        heading_str = f"Thread: {self.date}"
        tags_str = ""
        if bool(self.tags):
            tags_str = self.tag_pattern.format(self.tag_sep.join(self.tags))

        tag_pad = max(0, self.tag_col - len(heading_str))
        output.heading(2, f"{heading_str}{tag_pad*' '}{tags_str}")
        output.heading(3, "Main Thread")
        output.add(*self.main)

        output.heading(3, "Conversations: ", str(len(self.conversations)))
        for conv in self.conversations:
            if not bool(conv):
                continue

            output.heading(4, conv[0].at)
            output.add(*conv)

        output.heading(3, "Misc tweets: ", str(len(self.remainder)))
        output.add(*self.remainder)

        output.heading(3, "Links: ", str(len(self.links)))
        output.links(self.links)
        output.nl

        output.heading(3, "Media: ", str(len(self.media)))
        output.add(*["[[file:./{}][{}]]".format(TwitterThread.retarget_url(x, self.redirect_url), split(x)[1]) for x in self.media])
        output.nl

        return str(output)


@dataclass
class TwitterTweet:
    level        : int
    id_s         : str
    redirect_url : str
    is_quote     : bool                            = field(default=False)
    name         : str                             = field(init=False, default="Unknown")
    hash_tags    : List[str]                       = field(init=False, default_factory=list)
    quote        : Tuple[str, str, 'TwitterTweet'] = field(init=False, default=None)
    reply_to     : Tuple[str, str]                 = field(init=False, default=None)
    date         : 'datetime'                      = field(init=False, default_factory=datetime.datetime.now)
    media        : List[str]                       = field(default_factory=list)
    links        : List[str]                       = field(default_factory=list)

    fav          : int = 0
    retweet      : int = 0
    text         : str = ""

    permalink_f  : str =  "[[https://twitter.com/{}/status/{}][/{}/{}]]"

    @staticmethod
    def build(tweet, all_users, url_prefix, all_tweets, level=4, is_quote=False) -> 'TwitterTweet':
        obj                  = TwitterTweet(level, tweet['id_str'], is_quote=is_quote, redirect_url=url_prefix)

        try:
            obj.name         = all_users[tweet['user']['id_str']]['screen_name']
        except KeyError:
            pass

        try:
            obj.hash_tags    = [x['text'] for x in tweet['entities']['hashtags']]
        except KeyError:
            pass

        try:
            obj.reply_to     = (tweet['in_reply_to_screen_name'], tweet['in_reply_to_status_id_str'])
        except KeyError:
            pass

        try:
            obj.fav          = str(tweet['favorite_count'])
        except KeyError:
            pass

        try:
            obj.retweet      = str(tweet['retweet_count'])
        except KeyError:
            pass

        try:
            obj.date         = TwitterThread.parse_date(tweet['created_at'])
        except KeyError:
            pass

        try:
            obj.text         = tweet['full_text']
        except KeyError:
            pass

        try:
            quote_id         = tweet['quoted_status_id_str']
            quoted_tweet     = all_tweets[quote_id]
            quoted_user_name = all_users[quoted_tweet['user']['id_str']]['screen_name']
            quoted_tweet     = TwitterTweet.build(all_tweets[quote_id], all_users, url_prefix, all_tweets, level=level+1, is_quote=True)
            obj.quote        = (quoted_user_name, quote_id, quoted_tweet)
            obj.media += quoted_tweet.media
            obj.links += quoted_tweet.links
        except KeyError:
            pass

        try:
            urls             = tweet['entities']['urls']
            obj.links        = {x['expanded_url'] for x in urls}
        except KeyError:
            pass


        # TODO min urls in full_text, append full urls at end
        media, alt_texts = TwitterTweet.get_tweet_media(tweet)
        if bool(media):
            obj.media += media

        return obj

    def __str__(self):
        output     = OrgStrBuilder()
        tags       = ""
        tag_offset = 0
        if bool(self.hash_tags):
            tags       =  ":{}:".format(":".join(self.hash_tags))
            tag_offset =  max(0, 80-len(self.at))
            tags       = (tag_offset * " ") + tags

        quote_header = ""
        if self.is_quote:
            quote_header = "Quote: "
        output.heading(self.level, quote_header, self.at, tags)

        with output.drawer("PROPERTIES") as dr:
            dr.add("PERMALINK", self.permalink(self.name, self.id_s))
            if self.reply_to is not None and self.reply_to[0] is not None:
                dr.add("REPLY_TO", self.permalink(*self.reply_to))
            if self.quote is not None:
                dr.add("QUOTE", self.permalink(*self.quote[:2]))
            dr.add("FAVOURITE_COUNT", self.fav)
            dr.add("RETWEET_COUNT", self.retweet)
            dr.add("DATE", self.date.strftime(TwitterThread.date_re))
            if self.is_quote:
                dr.add("IS_QUOTE", "t")

        output.add(self.text)
        output.nl


        # TODO alt_texts
        if bool(self.media) and not self.is_quote:
            with output.drawer("MEDIA") as dr:
                dr.add_file_links(*[TwitterThread.retarget_url(x, self.redirect_url) for x in self.media])

        # Links
        if bool(self.links) and not self.is_quote:
            with output.drawer("LINKS") as dr:
                dr.add_keyless(*self.links)


        if self.quote is not None:
            output.add(self.quote[2])

        return str(output)

    @property
    def at(self):
        return f"@{self.name}"

    @staticmethod
    def permalink(name, id_s):
        return TwitterTweet.permalink_f.format(name, id_s, name, id_s)

    @staticmethod
    def get_tweet_media(tweet):
        media_urls = set()
        alt_texts  = []
        if 'entities' not in tweet:
            return media_urls, alt_texts

        try:
            media_entities = tweet['entities']['media']
            alt_texts += [m['ext_alt_text'] for m in media_entities if 'ext_alt_text' in m]
            media_urls.update([m['media_url_https'] for m in media_entities])

            videos   = [m['video_info'] for m in media_entities if m['type'] == "video"]
            urls     = [n['url'] for m in videos for n in m['variants'] if n['content_type'] == "video/mp4"]
            media_urls.update([x.split("?")[0] for x in urls])
        except KeyError:
            pass

        try:
            extended_entities = tweet['extended_entities']['media']
            media_urls.update([m['media_url_https'] for m in extended_entities])

            videos = [m['video_info'] for m in extended_entities if m['type'] == "video"]
            urls   = [n['url'] for m in videos for n in m['variants'] if n['content_type'] == "video/mp4"]
            media_urls.update([x.split("?")[0] for x in urls])
        except KeyError:
            pass

        return media_urls, alt_texts
