#!/usr/bin/env py
# pylint: disable=no-memberthon3
##-- imports
from __future__ import annotations

import pathlib as pl
import logging as logmod
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast, Final)

import requests
import twitter as tw
##-- end imports

logging = logmod.getLogger(__name__)

import webbrowser
import time
import json
import uuid
import doot
from doot import TomlAccess
from doot.tasker import BatchMixin
import tweepy

tweet_size         : Final = doot.config.on_fail(250, int).tool.doot.twitter.tweet_size()
tweet_img_types    : Final = doot.config.on_fail([".jpg", ".png", ".gif"], list).tool.doot.twitter.image_types()
tweet_image_size     : Final = doot.config.on_fail(4_500_000, int).tool.doot.twitter.max_image()
sleep_batch        : Final = doot.config.on_fail(2.0,   int|float).tool.doot.sleep_batch()
twitter_batch_size : Final = doot.config.on_fail(100, int).tool.doot.twitter.batch_size()

REPLY              : Final = 'in_reply_to_status_id_str'
QUOTE              : Final = 'quoted_status_id_str'
ID_STR             : Final = "id_str"

class TwitterMixin:

    twitter : TwitterApi
    todos : TweetTodoFile
    library_ids : set

    def setup_twitter(self, config:pl.Path|str):
        logging.info("---------- Initialising Twitter")
        secrets      = TomlAccess.load(pl.Path(config).expanduser())
        should_sleep = secrets.DEFAULT.sleep
        self.twitter = tw.Api(consumer_key=secrets.twitter.py.apiKey,
                              consumer_secret=secrets.twitter.py.apiSecret,
                              access_token_key=secrets.twitter.py.accessToken,
                              access_token_secret=secrets.twitter.py.accessSecret,
                              sleep_on_rate_limit=should_sleep,
                              tweet_mode='extended')

        return True

    def post_tweet(self, task):
        try:
            print("Posting Tweet")
            msg = task.values['msg']
            if len(msg) >= tweet_size:
                logging.warning("Resulting Tweet too long for twitter: %s\n%s", len(tweet_text), tweet_text)
                return { "twitter_result": False }
            else:
                result   = self.twitter.PostUpdate(msg)
                print("Tweet Posted")
                return {"twitter_result": True}
        except Exception as err:
            logging.warning("Twitter Post Failure: %s", err)
            return {"twitter_result": False}

    def post_twitter_image(self, task):
        try:
            print("Posting Image Tweet")
            msg          = task.values.get('msg', "")
            desc         = task.values.get('desc', '')
            the_file     = pl.Path(task.values['image']).expanduser()
            # if the_file.stat().st_size > tweet_image_size:
            #     the_file = compress_file(the_file)

            assert(the_file.exists())
            assert(the_file.stat().st_size < tweet_image_size)
            assert(the_file.suffix.lower() in tweet_img_types)
            result = self.twitter.UploadMediaChunked(str(the_file))
            self.twitter.PostMediaMetadata(result, alt_text=desc)
            result = self.twitter.PostUpdate(msg, media=result)
            print("Twitter Image Posted")
            return {"twitter_result": True }
        except Exception as err:
            print("Twitter Post Failed: ", str(err))
            return { "twitter_result": False }

    def tw_download_tweets(self, target_dir, missing_file, task):
        """ Download all tweets and related tweets for a list,
        """
        assert(target_dir.is_dir())
        logging.info("Downloading tweets to: %s", target_dir)
        queue : list[str] = task.values['target_ids']
        if not bool(queue):
            print("No Ids to Download")
            logging.info("No Ids to Download")
            return { "downloaded": [], "missing": [] }

        downloaded  = set()
        missing_ids = set()
        # Download in batches:
        while bool(queue):
            print("Download Queue Remaining: ", len(queue))
            # Pop group amount:
            current = list(set(queue[:twitter_batch_size]) - self.library_ids - missing_ids)
            queue   = queue[twitter_batch_size:]

            ## download tweets
            results = self.twitter.GetStatuses(current, trim_user=True)
            # update ids
            new_ids = [x.id_str for x in results]
            self.library_ids.update(new_ids)
            downloaded.update(new_ids)
            # Save as json
            self._save_downloaded(target_dir, results)

            # Add new referenced ids:
            for x in results:
                if REPLY in x._json and x._json[REPLY] is not None:
                    queue.append(str(x._json[REPLY]))
                if QUOTE in x._json and x._json[QUOTE] is not None:
                    queue.append(x._json[QUOTE])

            # Store missing ids
            batch_missing = set(current).difference([x._json[ID_STR] for x in results])
            if bool(batch_missing):
                missing_ids.update(batch_missing)
                self._save_missing(missing_file, batch_missing)
            if sleep_batch > 0:
                time.sleep(sleep_batch)


        return { "downloaded" : list(downloaded), "missing": list(missing_ids) }

    def _save_downloaded(self, target_dir, results):
        # add results to results dir
        new_json_file = target_dir / f"{uuid.uuid4().hex}.json"
        while new_json_file.exists():
            new_json_file = target_dir / f"{uuid.uuid4().hex}.json"

        dumped  = [json.dumps(x._json, indent=4) for x in results]
        as_json = "[{}]".format(",".join(dumped))
        new_json_file.write_text(as_json)


    def _save_missing(self, target_file, missing):
        with open(target_file, 'a') as f:
            f.write("\n" + "\n".join(missing))

class TweepyMixin:

    twitter : TwitterApi
    todos : TweetTodoFile
    library_ids : set

    def setup_twitter(self, config:pl.Path|str):
        logging.info("---------- Initialising Tweepy")
        secrets      = TomlAccess.load(pl.Path(config).expanduser())
        match secrets.twitter.method:
            case "v1bearer":
                self.setup_twitter_v1_bearer(secrets)
            case "v1uc":
                self.setup_twitter_v1_user_context(secrets)
            case "v2bearer":
                self.setup_twitter_v2_bearer(secrets)
            case "v2uc":
                self.setup_twitter_v2_user_context(secrets)
            case "v2pkce":
                self.setup_twitter_v2_pkce(secrets)
            case "v2pin":
                self.setup_twitter_v2_pin(secrets)

    def setup_twitter_v1_bearer(self, secrets):
        logging.info("---------- Initialising V1 OAuth2 Bearer")
        auth         = tweepy.OAuth2BearerHandler(secrets.twitter.py.bearerToken)
        self.twitter = tweepy.API(auth)

        return True

    def setup_twitter_v1_user_context(self, secrets):
        logging.info("---------- Initialising V1 OAuth1 User Context")
        auth         = tweepy.OAuth1UserHandler(
            secrets.twitter.py.apiKey, secrets.twitter.py.apiSecret,
            secrets.twitter.py.accessToken, secrets.twitter.py.accessSecret
            )
        self.twitter = tweepy.API(auth)

        return True

    def setup_twitter_v2_bearer(self, secrets):
        logging.info("---------- Initialising V2 OAuth2 Bearer")
        self.twitter = tweepy.Client(secrets.twitter.py.bearerToken)
        return True

    def setup_twitter_v2_user_context(self, secrets):
        logging.info("---------- Initialising V2 OAuth2 Bearer")
        self.twitter = tweepy.Client(
            consumer_key=secrets.twitter.py.apiKey,
            consumer_secret=secrets.twitter.py.apiSecret,
            access_token=secrets.twitter.py.accessToken,
            access_token_secret=secrets.twitter.py.accessSecret
            )
        return True

    def setup_twitter_v2_pkce(self, secrets):
        logging.info("---------- Initialising V2 OAuth2 Bearer")
        handler = tweepy.OAuth2UserHandler(
            client_id=secrets.twitter.py.clientID,
            client_secret=secrets.twitter.py.clientSecret,
            redirect_uri=secrets.twitter.py.redirect,
            scope=["bookmark.read", "tweet.read", "users.read"],
            )
        webbrowser.open(handler.get_authorization_url())
        verifier = input("Input response: ").strip()
        token = handler.fetch_token(verifier)
        assert(isinstance(token, dict))
        self.twitter = tweepy.Client(token['access_token'])
        breakpoint()
        pass
        return True

    def setup_twitter_v2_pin(self, secrets):
        logging.info("---------- Initialising V2 OAuth2 Bearer")
        oauth1_user_handler = tweepy.OAuth1UserHandler(
            secrets.twitter.py.apiKey, secrets.twitter.py.apiSecret,
            callback="oob"
        )
        webbrowser.open(oauth1_user_handler.get_authorization_url())
        verifier = input("Input PIN: ")
        access_token, access_token_secret = oauth1_user_handler.get_access_token(verifier)
        self.twitter = tweepy.Client(
            consumer_key=secrets.twitter.py.apiKey,
            consumer_secret=secrets.twitter.py.apiSecret,
            access_token=access_token,
            access_token_secret=access_token_secret
            )


    def get_bookmarks(self):
        return self.twitter.get_bookmarks()
