#!/usr/bin/env python3
"""
A Collection of dataclasses which reduce to json
"""
##-- imports
from __future__ import annotations

import datetime
import json
import logging as logmod
import pathlib as pl
import re
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from itertools import cycle
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from uuid import uuid1

import networkx as nx
from doot.utils.formats.org_builder import OrgStrBuilder

##-- end imports

logging = logmod.getLogger(__name__)

media_dict : Final[Callable] = lambda: defaultdict(list)

@dataclass
class OrgThreadWriter:
    """ Given a thread object, build a string representation for it
    redirecting absolute media paths to relative
    """

    user          : str
    date          : datetime.datetime
    tags          : set[str]
    main          : list[TwitterTweet]       = field(default_factory=list)
    conversations : list[List[TwitterTweet]] = field(default_factory=list)
    uses          : set[str]                 = field(default_factory=set)
    links         : set[str]                 = field(default_factory=set)
    media         : dict                     = field(default_factory=media_dict)

    redirect_url  : str = "{}_files"
    date_re       : str = r"%a %b %d %H:%M:%S +0000 %Y"
    tag_pattern   : str = ":{}:"
    tag_sep       : str = ":"
    tag_col       : int = 80
    file_link_pattern : str = "[[file:./{}][{}]]"

    @staticmethod
    def build(thread:dict, tweets:list, users:list, source_tags:dict[str, set[str]]) -> OrgThreadWriter:
        logging.info("Creating thread")

        main_thread_ids = thread['main_thread']
        sub_thread_ids  = thread['rest']
        quote_ids       = thread['quotes']
        base_user       = thread["base_user"]
        tweet_lookup    = {x['id_str'] : x for x in tweets}
        tags            = {y.strip() for x in main_thread_ids for y in source_tags[x] if x in source_tags}
        users_lookup    = {x['id_str'] : x for x in users}

        min_thread_date = min(((x,OrgThreadWriter.parse_date(tweet_lookup[x]['created_at']))
                              for x in main_thread_ids if x in tweet_lookup), key=lambda v:v[1])
        thread_date = min_thread_date[1]

        obj = OrgThreadWriter(base_user, thread_date, tags)

        # add tweets of main thread
        for x in main_thread_ids:
            if x not in tweet_lookup:
                obj.main.append(TwitterTweet("null", base_user))
                continue

            obj.add_use(x)
            tweet_obj = TwitterTweet.build(base_user, tweet_lookup[x], users_lookup, tweet_lookup)
            obj.main.append(tweet_obj)
            for key, values in tweet_obj.media.items():
                obj.media[key] += values

            obj.links.update(tweet_obj.links)

        # Add sub conversations
        for conv in sub_thread_ids:
            conv_list = []
            for x in conv:
                if x not in tweet_lookup:
                    conv_list.append(TwitterTweet("null", base_user, level=5))
                    continue
                obj.add_use(x)
                tweet_obj = TwitterTweet.build(base_user, tweet_lookup[x], users_lookup, tweet_lookup, level=5)
                conv_list.append(tweet_obj)
                obj.media.update(tweet_obj.media)
                obj.links.update(tweet_obj.links)

            obj.conversations.append(conv_list)

        return obj

    def add_use(self, value):
        """
        Record a use of a tweet id
        """
        self.uses.add(value)

    @staticmethod
    def retarget_url(base, url):
        base_p = pl.Path(OrgThreadWriter.redirect_url.format(base))
        url_p  = pl.Path(url)
        logging.debug("Retargeting URL: %s", url_p.name)
        return str(base_p / url_p.name)

    @staticmethod
    def parse_date( a_str) -> datetime:
        """ Parse a twitter 'created_at' string to a date """
        return datetime.datetime.strptime(a_str, OrgThreadWriter.date_re)

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

        output.heading(3, "Links: ", str(len(self.links)))
        output.links(self.links)
        output.nl

        output.heading(3, "Media: ", str(len(self.media)))
        retarget = lambda x: (OrgThreadWriter.retarget_url(self.user, x['url']), pl.Path(x['url']).name)
        media_urls = []
        media_urls += [retarget(media) for media in self.media.get('photo', [])]
        media_urls += [retarget(media) for media in self.media.get('video', [])]

        media_local =[self.file_link_pattern.format(*x) for x in media_urls]
        output.add(*media_local)
        output.nl

        return str(output)

@dataclass
class TwitterTweet:
    id_s         : str
    base_user    : str
    is_quote     : bool                          = field(default=False)
    name         : str                           = field(init=False, default="Unknown")
    hash_tags    : List[str]                     = field(init=False, default_factory=list)
    quote        : Tuple[str, str, TwitterTweet] = field(init=False, default=None)
    reply_to     : Tuple[str, str]               = field(init=False, default=None)
    date         : datetime                      = field(init=False, default_factory=datetime.datetime.now)
    media        : dict                          = field(default_factory=media_dict)
    links        : list[str]                     = field(default_factory=list)
    level        : int                           = field(default=4)

    fav          : int = 0
    retweet      : int = 0
    text         : str = ""

    permalink_f  : str =  "[[https://twitter.com/{}/status/{}][/{}/{}]]"

    @staticmethod
    def build(base, tweet, users, tweet_lookup, level=4, is_quote=False) -> TwitterTweet:
        obj                  = TwitterTweet(tweet['id_str'], base, is_quote=is_quote, level=level)

        obj.name         = users.get(tweet.get('user', {}).get('id_str', None), {}).get('screen_name', None)
        obj.hash_tags    = [x.get('text', "") for x in tweet.get('entities', {}).get('hashtags', [])]
        obj.reply_to     = (tweet.get('in_reply_to_screen_name', None), tweet.get('in_reply_to_status_id_str', None))
        obj.fav          = str(tweet.get('favorite_count', 0))
        obj.retweet      = str(tweet.get('retweet_count', 0))
        obj.text         = tweet.get('full_text', "")
        date_str : None | str = tweet.get('created_at', None)
        if date_str:
            obj.date         = OrgThreadWriter.parse_date(date_str)

        urls             = tweet.get('entities', {}).get('urls', [])
        obj.links        = {x.get('expanded_url', None) for x in urls}

        try:
            quote_id         = tweet.get('quoted_status_id_str', None)
            quoted_tweet     = tweet_lookup.get(quote_id, {})
            quote_user_id    = quoted_tweet.get('user', {}).get('id_str', None)
            quoted_user_name = users.get(quote_user_id, {}).get('screen_name', "Unknown")
            quoted_tweet     = TwitterTweet.build(base, tweet_lookup[quote_id], users, tweet_lookup, level=level+1, is_quote=True)
            obj.quote        = (quoted_user_name, quote_id, quoted_tweet)
            # obj.media += quoted_tweet.media
            obj.links.update(quoted_tweet.links)
        except KeyError:
            pass

        media = TwitterTweet.get_tweet_media(tweet)
        obj.media = media
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
            dr.add("DATE", self.date.strftime(OrgThreadWriter.date_re))
            if self.is_quote:
                dr.add("IS_QUOTE", "t")

        output.add(re.sub("\n\*", "\n-*", self.text))
        output.nl

        retarget= lambda x: OrgThreadWriter.retarget_url(self.base_user, x['url'])
        media_urls = []
        media_urls += [retarget(media) for media in self.media.get('photo', [])]
        media_urls += [retarget(media) for media in self.media.get('video', [])]

        if bool(media_urls):
            with output.drawer("MEDIA") as dr:
                dr.add_file_links(*media_urls)

        # Links
        if bool(self.links):
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
    def get_tweet_media(tweet) -> dict:
        media = media_dict()
        to_process = []
        to_process += tweet.get('entities', {}).get('media', [])
        to_process += tweet.get('extended_entities', {}).get('media', [])

        for ent in to_process:
            url        = ent.get('media_url_https', "")
            # filename   = pl.Path(url).name

            datum = {
                "url"          : url,
                "expanded_url" : ent.get("expanded_url", ""),
                "alt_text"     : ent.get('ext_alt_text', ""),
                "type"         : ent.get('type', "n/a"),
                }

            media[datum["type"]].append(datum)

            if datum['type'] == "video":
                video_datum = datum.copy()
                mp4s = [x for x in ent.get('video_info', {}).get('variants', []) if x.get('content_type', None) == "video/mp4"]
                best_variant = max(mp4s, key=lambda x: x.get('bitrate', 0))
                best_url = best_variant.get('url', "").split("?")[0]
                if bool(best_url):
                    video_datum['url'] = best_url
                    media['video'].append(video_datum)

        return media
