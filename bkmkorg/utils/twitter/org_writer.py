#!/usr/bin/env python3
#!/usr/bin/env python3
"""
A Collection of dataclasses which reduce to json
"""
import json
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

from os import listdir, mkdir
from collections import defaultdict
from uuid import uuid1
import datetime
import logging as root_logger
import networkx as nx
logging = root_logger.getLogger(__name__)

from bkmkorg.utils.download.twitter import download_tweets
from bkmkorg.utils.download.media import download_media
from bkmkorg.utils.org.string_builder import OrgStrBuilder

@dataclass
class TwitterOrg:
    """ Create an Org File from twitter user summary """

    summary_path : str
    dir_s        : str

    tag_lookup   : 'TweetTodoFile'
    user_lookup  : Dict[str, Any]


    org_pattern   : str = field(default="{}.org")
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
        return join(self.dir_s, self.org_pattern.format(self._id_s))

    @property
    def relative_files_path(self):
        return self.files_pattern.format(self._id_s)

    @property
    def absolute_files_path(self):
        return join(self.dir_s, self.relative_files_path)

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
        output.drawer("PROPERTIES")
        if 'name' in self._summary['user']:
            output.drawer_prop("NAME", self._summary['user']['name'])
        if 'followers_count' in self._summary['user']:
            output.drawer_prop("FOLLOWERS", self._summary['user']['followers_count'])
        if 'description' in self._summary['user']:
            output.drawer_prop("DESCRIPTION", self._summary['user']['description'])
        if 'location' in self._summary['user']:
            output.drawer_prop("LOCATION", self._summary['user']['location'])
        if 'url' in self._summary['user']:
            output.drawer_prop("URL", "[[{}]]".format(self._summary['user']['url']))
        output.drawer_prop("TWITTER-BUFFER", "t")
        output.drawer_end()

        self._output += output


    def build_threads(self):
        for thread in self._summary['threads']:
            thread = TwitterThread.build(thread,
                                         self.relative_files_path,
                                         self.user_lookup,
                                         self.tweets,
                                         self.tag_lookup)

            self._output.append(thread)

    def build_unused(self):
        unused_tweets = set(self.tweet_lookup.keys()).difference(self._used)
        if bool(unused_tweets):
            self._output.append("*** Unused Tweets")
            self._output += [TwitterTweet.build(self.tweet_lookup[x],
                                                self.user_lookup,
                                                self.relative_files_path) for x in unused_tweets]

    def download_media(self):
        # copy media to correct output files dir
        if not bool(self._media):
            return

        if not exists(self.absolute_files_path) and bool(self._media):
            mkdir(self.absolute_files_path)

        if bool(self._media):
            download_media(self.absolute_files_path, self._media)

@dataclass
class TwitterThread:

    redirect_url  : str
    date          : datetime.datetime
    tags          : Set[str]
    main          : List[TwitterTweet]
    conversations : List[List[TwitterTweet]]
    links         : List[str]
    media         : List[str]

    date_re       : str = r"%a %b %d %H:%M:%S +0000 %Y"

    @staticmethod
    def build(thread, redirect_url, all_users, tweets, source_ids) -> 'TwitterThread':
        logging.info("Creating thread")
        assert(isinstance(thread, dict))
        assert(isinstance(all_users, dict))

        main_thread      = [tweets[x] for x in thread['main_thread'] if x in tweets]
        thread_tweet_ids = thread['total']

        if not bool(main_thread):
            return None

        date = TwitterThread.parse_date(main_thread[0]['created_at'])
        tags = set([y.strip() for x in thread_tweet_ids for y in source_ids.mapping[x].split(",") if y != ""])

        obj = TwitterThread(redirect_url, date, tags)

        # add tweets of main thread
        used_tweets = [x['id_str'] for x in main_thread]
        for x in main_thread:
            tweet_obj = TwitterTweet.build(x, all_users, redirect_url)
            obj.main.append(tweet_obj)
            obj.media.update(tweet_obj.media)
            obj.links.update(tweet_obj.links)

        return obj

    @staticmethod
    def retarget_url(url, new_target_dir):
        logging.debug("Retargeting URL: {} to {}".format(split(url)[1], new_target_dir))
        return join(new_target_dir, split(url)[1])

    @staticmethod
    def parse_date( a_str) -> 'datetime':
        """ Parse a twitter 'created_at' string to a date """
        return datetime.datetime.strptime(a_str, TwitterThread.date_re)



    def __str__(self):
        output = OrgStrBuilder()

        tags_str = ""
        if bool(self.tags):
            tags_str = "          :{}:".format(":".join(self.tags))

        output.heading(2, "Thread:", self.date, tags_str)
        output.heading(3, "Main Thread")
        # TODO main thread

        output.heading(3, "Conversations")
        for conv in self.conversations:
            if not bool(conv):
                continue
            missing_tweets = [x for x in conv if x not in tweets]
            conv_tweets    = [tweets[x] for x in conv if x in tweets]
            if not bool(conv_tweets):
                logging.info("Empty Conversation: {}".format(conv))
                continue

            conv_links = []
            conv_media = []

            screen_name = conv_tweets[0]['user']['id_str']
            if screen_name in all_users:
                screen_name = all_users[screen_name]['screen_name']

            output.heading(4, "Conversation:", screen_name)


            # Add tweets
            new_tweets = [x['id_str'] for x in conv_tweets]
            used_tweets.update(new_tweets)

            output.add(*[TwitterTweet.build(x, all_users, self.redirect_url, level=5) for x in conv_tweets])

            if bool(missing_tweets):
                output.heading(5, "MISSING")
                # TODO output.add(*[x for x in missing_tweets])

        output.heading(3, "Links")
        output.links(self.links)
        output.nl

        output.heading(3, "Media")
        output += ["[[file:./{}][{}]]".format(TwitterThread.retarget_url(x, self.redirect_url), split(x)[1]) for x in self.media]
        output.nl

        return str(output)

@dataclass
class TwitterTweet:
    level       : int
    id_s        : str
    name        : str = field(default="Unknown")
    is_quote    : bool = field(default=False)
    hash_tags   : List[str] = field(default_factory=list)
    reply_to    : Tuple[str, str]
    quote       : Tuple[str, str, 'TwitterTweet']
    fav         : int
    retweet     : int
    date        : 'datetime'
    text        : str
    media       : List[Tuple[str, str]] = field(default_factory=list)
    links       : List[str] = field(default_factory=list)


    permalink_f   : "[[https://twitter.com/{}/status/{}][/{}/{}]]"

    @staticmethod
    def build(tweet, all_users, url_prefix, level=4, is_quote=False) -> 'TwitterTweet':
        obj = None
        try:
            screen_name = all_users[tweet['user']['id_str']]['screen_name']
            hashtags = [x['text'] for x in tweet['entities']['hashtags']]
            obj = TwitterTweet(level, screen_name)
        except KeyError as e:
            logging.warning("Unknown Screen name: {}".format(tweet['user']['id_str']))
            hashtags = [x['text'] for x in tweet['entities']['hashtags']]
            obj = TwitterTweet(level, hash_tags=hashtags)


        # output.append(":PERMALINK: [[https://twitter.com/{}/status/{}][/{}/{}]]".format(screen_name,
        #                                                                                 tweet['id_str'],
        #                                                                                 screen_name,
        #                                                                                 tweet['id_str']))
        # if tweet["in_reply_to_status_id_str"] is not None:
        #     output.append(":REPLY_TO: [[https://twitter.com/{}/status/{}][/{}/{}]]".format(tweet['in_reply_to_screen_name'],
        #                                                                                     str(tweet['in_reply_to_status_id_str']),
        #                                                                                     tweet['in_reply_to_screen_name'],
        #                                                                                     str(tweet['in_reply_to_status_id_str'])))

        # if "quoted_status_id_str" in tweet:
        #     quote_name = tweet['quoted_status_id_str']
        #     if quote_name in all_users:
        #         quote_name = all_users[tweet['quoted_status_id_str']]['screen_name']

        #     output.append(":QUOTE: [[https://twitter.com/{}/status/{}][/{}/{}]]".format(quote_name,
        #                                                                                 tweet['quoted_status_id_str'],
        #                                                                                 quote_name,
        #                                                                                 tweet['quoted_status_id_str']))
        # # in reply to
        # if 'favorite_count' in tweet:
        #     output.append(":FAVORITE_COUNT: {}".format(tweet['favorite_count']))
        # if 'retweet_count' in tweet:
        #     output.append(":RETWEET_COUNT: {}".format(tweet['retweet_count']))

        # output.append(":DATE: {}".format(TwitterThread.parse_date(tweet['created_at'])))
        # if is_quote:
        #     output.append(":IS_QUOTE: t")
        # output.append(":END:")

        # # add tweet contents
        # output.append(tweet['full_text'])


        # quoted_status -> quote -> tweet
        # qlinks = []
        # qmedia = []
        # if "quoted_status" in tweet:
        #     output.append("")
        #     quote_level = level + 1
        #     qresult, qmedia, qlinks = TwitterTweet.build(tweet['quoted_status'], all_users, url_prefix, level=quote_level)
        #     output.append(qresult)

        # # TODO min urls in full_text, append full urls at end
        # media, alt_texts = TwitterTweet.get_tweet_media(tweet)

        # output.append("")
        # output += alt_texts

        # # add tweet urls
        # output.append("")
        # links = set([x['expanded_url'] for x in tweet['entities']['urls']])
        # output += ["[[{}]]".format(x) for x in links]

        # if bool(media):
        #     output += "\n"
        #     output += ["[[file:./{}][{}]]".format(TwitterThread.retarget_url(x, url_prefix), split(x)[1]) for x in media]


        # output.append("")

        # total_media = set(media)
        # total_media.update(qmedia)
        # total_links = set(links)
        # total_links.update(qlinks)

        return obj

    def __str__(self):
        output = OrgStrBuilder()
        output.heading(self.level, self.at, ":{}:".format(":".join(self.hash_tags)))

        output.drawer("PROPERTIES")
        output.drawer_prop("PERMALINK", self.permalink(self.name, self.id_s))
        if self.reply_to:
            output.drawer_prop("REPLY_TO", self.permalink(*self.reply_to))
        if self.quote:
            output.drawer_prop("QUOTE", self.permalink(*self.quote[:2]))
        output.drawer_prop("FAVOURITE_COUNT", self.fav)
        output.drawer_prop("RETWEET_COUNT", self.retweet)
        output.drawer_prop("DATE", TwitterThread.parse_date(self.date))
        if self.is_quote:
            output.drawer_prop("IS_QUOTE", "t")

        output.drawer_end()

        output.add(self.text)

        if self.quote:
            # TODO do a drawer for quotes
            pass

        # TODO media + alt_texts

        # TODO Links

        return str(output)

    @property
    def at(self):
        return f"@{self.name}"

    @staticmethod
    def permalink(name, id_s):
        return TwitterTweet.permalink_f.format(name, id_s, name, id_s)

    @staticmethod
    def get_tweet_media(tweet):
        # add tweet media
        media     = set()
        alt_texts = []
        if 'entities' not in tweet:
            breakpoint()
            return media

        if 'media' in tweet['entities']:
            alt_texts += [m['ext_alt_text'] for m in tweet['entities']['media'] if 'ext_alt_text' in m]
            media.update([m['media_url'] for m in tweet['entities']['media']])

            videos   = [m['video_info'] for m in tweet['entities']['media'] if m['type'] == "video"]
            urls     = [n['url'] for m in videos for n in m['variants'] if n['content_type'] == "video/mp4"]
            media.update([x.split("?")[0] for x in urls])

        if 'extended_entities' in tweet and 'media' in tweet['extended_entities']:
            media.update([m['media_url'] for m in tweet['extended_entities']['media']])

            videos = [m['video_info'] for m in tweet['extended_entities']['media'] if m['type'] == "video"]
            urls = [n['url'] for m in videos for n in m['variants'] if n['content_type'] == "video/mp4"]
            media.update([x.split("?")[0] for x in urls])

        return media, alt_texts


