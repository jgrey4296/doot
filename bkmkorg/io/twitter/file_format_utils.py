from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

import datetime
import json
import logging as root_logger
import uuid
from os import listdir, mkdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from shutil import copyfile, rmtree

import networkx as nx
from bkmkorg.io.twitter.dfs_utils import dfs_chains
from bkmkorg.io.twitter.download_utils import download_tweets, download_media

logging = root_logger.getLogger(__name__)

USER_FILE_TEMPLATE = "user_{}.json"
DATE_RE = r"%a %b %d %H:%M:%S +0000 %Y"

def create_component_files(components, tweet_dir, component_dir, di_graph, twit=None):
    """ Create intermediate component files of tweet threads """
    logging.info("Creating {} component files\n\tfrom: {}\n\tto: {}".format(len(components), tweet_dir, component_dir))
    id_map = {}
    for comp_set in components:
        # Then to each id in that component:
        component_filename = join(component_dir, "component_{}.json".format(uuid.uuid1()))
        assert(not exists(component_filename))
        for x in comp_set:
            if x not in id_map:
                id_map[x] = []
            id_map[x].append(component_filename)


    # create separate component files
    logging.info("Copying to component files")
    missing_ids = set()
    json_files = [join(tweet_dir, x) for x in listdir(tweet_dir) if splitext(x)[1] == ".json"]
    for jfile in json_files:
        with open(jfile, 'r') as f:
            data = json.load(f, strict=False)

        for tweet in data:
            # Add tweet to any of its components
            id_str = tweet['id_str']
            if id_str not in id_map:
                missing_ids.add(id_str)
                continue

            component_filenames = set(id_map[id_str])
            for comp_f_name in component_filenames:
                new_file = not exists(comp_f_name)
                with open(comp_f_name, 'a') as f:
                    if new_file:
                        f.write("[")
                    else:
                        f.write(",")
                    f.write(json.dumps(tweet, indent=4))

            # Add tweet to any component that quotes it
            quoter_edges = [x for x in di_graph[id_str] if di_graph[id_str][x] == "quote"]
            discovered = set()
            while bool(quoter_edges):
                quoter_id = quoter_edges.pop(0)
                discovered.add(quoter_id)
                additional_quotes = [x for x in di_graph[quoter_id] if di_graph[quoter_id][x] == "quote"]
                quoter_edges += [x not in discovered for x in additional_quotes]


                component_filenames = set(id_map[quoter_id])
                for comp_f_name in component_filenames:
                    new_file = not exists(comp_f_name)
                    with open(comp_f_name, 'a') as f:
                        if new_file:
                            f.write("[")
                        else:
                            f.write(",")
                        f.write(json.dumps(tweet, indent=4))

    if bool(missing_ids):
        logging.info("Missing: {}".format(missing_ids))
        if not download_tweets(twit, tweet_dir, missing_ids):
            exit()


    # After every file is finished, add a final ]
    for x in [join(component_dir, x) for x in listdir(component_dir) if splitext(x)[1] == ".json"]:
        with open(x, 'a') as f:
            f.write(']')


def construct_user_summaries(component_dir, combined_threads_dir, total_users):
    """ collate threads together by originating user """
    logging.info("Constructing summaries\n\tfrom: {} \n\tto: {}".format(component_dir, combined_threads_dir))
    user_lookup = total_users
    # Create final orgs, grouped by head user
    components = [join(component_dir, x) for x in listdir(component_dir) if splitext(x)[1] == ".json"]
    for comp in components:
        logging.info("Constructing Summary for: {}".format(comp))
        # read comp
        with open(comp, 'r') as f:
            data = json.load(f, strict=False)

        if not bool(data):
            continue

        # Get leaves
        tweets = {x['id_str'] : x for x in data}
        user_counts = {t['user']['id_str'] : 0 for t in data}
        for x in data:
            user_counts[x['user']['id_str']] += 1


        head_user = max(user_counts.items(), key=lambda x: x[1])[0]
        screen_name = str(head_user)
        if head_user in user_lookup:
            screen_name = user_lookup[head_user]['screen_name']

        logging.info("Constructing graph")
        graph  = nx.DiGraph()
        quotes = set()
        roots  = set()
        for tweet in data:
            if tweet['in_reply_to_status_id_str'] is not None:
                graph.add_edge(tweet['in_reply_to_status_id_str'], tweet['id_str'])
            else:
                graph.add_node(tweet['id_str'])
                roots.add(tweet['id_str'])

            if 'quoted_status_id_str' in tweet and tweet['quoted_status_id_str'] is not None:
                quotes.add(tweet['quoted_status_id_str'])

        # dfs to get longest chain
        chains = []

        if bool(roots):
            chains = dfs_chains(graph, roots)

        if not bool(chains):
            chains = [list(roots.union(quotes))]

        # Assign main thread
        main_thread = max(chains, key=lambda x: len(x))
        main_set    = set(main_thread)
        main_index  = chains.index(main_thread)

        # assign secondary conversations
        rest = chains[:main_index] + chains[main_index+1:]

        rest = [x for x in rest if bool(x)]
        cleaned_rest = []
        for thread in rest:
            cleaned = [x for x in thread if x not in main_set]
            cleaned_rest.append(cleaned)
            main_set.update(cleaned)

        # create user file if not exist
        user_file = join(combined_threads_dir, USER_FILE_TEMPLATE.format(screen_name))
        user_data = {'has_media' : False}
        if exists(user_file):
            with open(user_file, 'r') as f:
                user_data = json.load(f, strict=False)

        if 'user' not in user_data:
            if head_user in user_lookup:
                user_data['user'] = user_lookup[head_user]
            else:
                user_data['user'] = {'screen_name': screen_name}
            user_data['threads'] = []
            user_data['tweets'] = {}

        quote_list = list(quotes)
        has_media = any([bool(get_tweet_media(x)) for x in tweets.values()])
        user_data['has_media'] = user_data['has_media'] or has_media

        user_data['threads'].append({'main_thread' : main_thread,
                                     'rest' : cleaned_rest,
                                     'quotes' : quote_list})


        user_data['tweets'].update(tweets)


        # write out user file
        with open(user_file, 'w') as f:
            json.dump(user_data, f, indent=4)


def construct_org_files(combined_threads_dir, org_dir, all_users):
    logging.info("Constructing org files from: {} \n\tto: {}".format(combined_threads_dir, org_dir))
    # get all user summary jsons
    user_summaries = [join(combined_threads_dir, x) for x in listdir(combined_threads_dir) if splitext(x)[1] == ".json"]

    for summary in user_summaries:
        with open(summary, 'r') as f:
            data = json.load(f, strict=False)

        tweets = data['tweets']
        if not bool(tweets):
            logging.info(f"Skipping Empty User: {data['user']['screen_name']}")
            continue


        out_file  = join(org_dir, "{}.org".format(data['user']['screen_name']))
        out_files_dir_last = "{}_files".format(data['user']['screen_name'])
        out_files_dir = join(org_dir, out_files_dir_last)

        if exists(out_file):
            logging.info(f"Skipping medialess user: {data['user']['screen_name']}")
            continue

        media = set()
        output = []

        # Add initial line
        output.append("* {}'s Threads".format(data['user']['screen_name']))
        output.append(":PROPERTIES:")
        if 'name' in data['user']:
            output.append(":NAME: {}".format(data['user']['name']))
        if 'followers_count' in data['user']:
            output.append(":FOLLOWERS: {}".format(data['user']['followers_count']))
        if 'description' in data['user']:
            output.append(":DESCRIPTION: {}".format(data['user']['description']))
        if 'location' in data['user']:
            output.append(":LOCATION: {}".format(data['user']['location']))
        if 'url' in data['user']:
            output.append(":URL: [[{}]]".format(data['user']['url']))
        output.append(":TWITTER-BUFFER: t")
        output.append(":END:")

        # add conversations
        used_tweets = set()
        for thread in data['threads']:
            thread_out, thread_media, used = thread_to_strings(thread, out_files_dir_last, all_users, tweets)
            output += thread_out
            used_tweets.update(used)
            media.update(thread_media)

        unused_tweets = set(tweets.keys()).difference(used_tweets)
        if bool(unused_tweets):
            output.append("*** Unused Tweets")
            output += [tweet_to_string(tweets[x], all_users, out_files_dir_last)[0] for x in unused_tweets]

        with open(out_file, 'w') as f:
            f.write("\n".join(output))

        if not bool(media):
            continue

        # copy media to correct output files dir
        if not exists(out_files_dir) and bool(media):
            mkdir(out_files_dir)

        if bool(media):
            download_media(out_files_dir, media)

def thread_to_strings(thread, redirect_url, all_users, tweets):
    logging.info("Creating thread")
    assert(isinstance(thread, dict))
    assert(isinstance(all_users, dict))
    links = set()
    media = set()
    used_tweets = set()
    output = []
    main_thread = [tweets[x] for x in thread['main_thread'] if x in tweets]
    if not bool(main_thread):
        return output, media, used_tweets

    quotes = thread['quotes']
    # Add user info
    # append tweets in order as a thread
    date = parse_date(main_thread[0]['created_at'])

    # TODO: format this
    output.append("** Thread: {}".format(date))
    output.append("*** Main Thread")
    # add tweets of main thread
    used_tweets.update([x['id_str'] for x in main_thread])
    for x in main_thread:
        mresult, mmedia, mlinks = tweet_to_string(x, all_users, redirect_url)
        output.append(mresult)
        media.update(mmedia)
        links.update(mlinks)


    output.append("*** Conversations")
    for conv in thread['rest']:
        if not bool(conv):
            continue
        missing_tweets = [x for x in conv if x not in tweets]
        conv_tweets = [tweets[x] for x in conv if x in tweets]
        if not bool(conv_tweets):
            logging.info("Empty Conversation: {}".format(conv))
            continue
        # TODO get links and media
        conv_links = []
        conv_media = []

        screen_name = conv_tweets[0]['user']['id_str']
        if screen_name in all_users:
            screen_name = all_users[screen_name]['screen_name']
        output.append("**** Conversation: {}".format(screen_name))

        # Add tweets
        new_tweets = [x['id_str'] for x in conv_tweets]
        used_tweets.update(new_tweets)
        for x in conv_tweets:
            mresult, mmedia, mlinks = tweet_to_string(x, all_users, redirect_url, level=5)
            output.append(mresult)
            media.update(mmedia)
            links.update(mlinks)

        if bool(missing_tweets):
            output.append("***** MISSING")
            output += [x for x in missing_tweets]

    output.append("*** Links")
    output += ["[[{}]]".format(x) for x in links]
    output.append("")

    output.append("*** Media")
    output += ["[[file:./{}][{}]]".format(retarget_url(x, redirect_url), split(x)[1]) for x in media]

    output.append("")
    return output, media, used_tweets

def tweet_to_string(tweet, all_users, url_prefix, level=4, is_quote=False):
    output = []

    indent = "*" * level
    screen_name = "Unknown"
    try:
        screen_name = all_users[tweet['user']['id_str']]['screen_name']
    except KeyError as e:
        logging.warning("Unknown Screen name: {}".format(tweet['user']['id_str']))

    try:
        hashtags = [x['text'] for x in tweet['entities']['hashtags']]
    except KeyError as e:
        breakpoint()

    hash_str = ""
    if bool(hashtags):
        hash_str = ":{}:".format(":".join(hashtags))
    output.append("{} @{}          {}".format(indent, screen_name, hash_str))

    # Add Details drawer
    output.append(":PROPERTIES:")
    output.append(":PERMALINK: [[https://twitter.com/{}/status/{}][/{}/{}]]".format(screen_name,
                                                                                      tweet['id_str'],
                                                                                      screen_name,
                                                                                      tweet['id_str']))
    if tweet["in_reply_to_status_id_str"] is not None:
        output.append(":REPLY_TO: [[https://twitter.com/{}/status/{}][/{}/{}]]".format(tweet['in_reply_to_screen_name'],
                                                                                         str(tweet['in_reply_to_status_id_str']),
                                                                                         tweet['in_reply_to_screen_name'],
                                                                                         str(tweet['in_reply_to_status_id_str'])))

    if "quoted_status_id_str" in tweet:
        quote_name = tweet['quoted_status_id_str']
        if quote_name in all_users:
            quote_name = all_users[tweet['quoted_status_id_str']]['screen_name']

        output.append(":QUOTE: [[https://twitter.com/{}/status/{}][/{}/{}]]".format(quote_name,
                                                                                      tweet['quoted_status_id_str'],
                                                                                      quote_name,
                                                                                      tweet['quoted_status_id_str']))
    # in reply to
    if 'favorite_count' in tweet:
        output.append(":FAVORITE_COUNT: {}".format(tweet['favorite_count']))
    if 'retweet_count' in tweet:
        output.append(":RETWEET_COUNT: {}".format(tweet['retweet_count']))

    output.append(":DATE: {}".format(parse_date(tweet['created_at'])))
    if is_quote:
        output.append(":IS_QUOTE: t")
    output.append(":END:")

    # add tweet contents
    output.append(tweet['full_text'])


    # quoted_status -> quote -> tweet
    qlinks = []
    qmedia = []
    if "quoted_status" in tweet:
        output.append("")
        quote_level = level + 1
        qresult, qmedia, qlinks = tweet_to_string(tweet['quoted_status'], all_users, url_prefix, level=quote_level)
        output.append(qresult)

    media = get_tweet_media(tweet)

    # add tweet urls
    output.append("")
    links = set([x['expanded_url'] for x in tweet['entities']['urls']])
    output += ["[[{}]]".format(x) for x in links]

    if bool(media):
        output += "\n"
        output += ["[[file:./{}][{}]]".format(retarget_url(x, url_prefix), split(x)[1]) for x in media]


    output.append("")

    total_media = set(media)
    total_media.update(qmedia)
    total_links = set(links)
    total_links.update(qlinks)

    return "\n".join(output), list(total_media), total_links

def parse_date(a_str):
    """ Parse a twitter 'created_at' string to a date """
    return datetime.datetime.strptime(a_str, DATE_RE)

def retarget_url(url, new_target_dir):
    logging.debug("Retargeting URL: {} to {}".format(split(url)[1], new_target_dir))
    return join(new_target_dir, split(url)[1])

def assemble_threads(json_dir):
    """ Create a graph of tweet replies and quotes """
    logging.info("Assembling threads graph from: {}".format(json_dir))
    json_files = [join(json_dir, x) for x in listdir(json_dir) if splitext(x)[1] == ".json"]
    di_graph = nx.DiGraph()
    for jfile in json_files:
        # load in each json,
        with open(jfile, 'r') as f:
            data = json.load(f, strict=False)

        # construct connection graph
        for entry in data:
            # get tweet id, reply_id, quote_id
            tweet_id = entry['id_str']
            di_graph.add_node(tweet_id, source_file=jfile)

            if 'in_reply_to_status_id_str' in entry and entry['in_reply_to_status_id_str']:
                # link tweets
                di_graph.add_edge(tweet_id,
                                  str(entry['in_reply_to_status_id_str']),
                                  type="reply")

            if 'quoted_status_id_str' in entry and entry['quoted_status_id_str']:
                di_graph.add_edge(tweet_id,
                                  str(entry['quoted_status_id_str']),
                                  type="quote")

    return di_graph

def get_tweet_media(tweet):
    # add tweet media
    media = set()
    if 'entities' not in tweet:
        breakpoint()
        return media

    if 'media' in tweet['entities']:
        media.update([m['media_url'] for m in tweet['entities']['media']])

        videos = [m['video_info'] for m in tweet['entities']['media'] if m['type'] == "video"]
        urls = [n['url'] for m in videos for n in m['variants'] if n['content_type'] == "video/mp4"]
        media.update([x.split("?")[0] for x in urls])

    if 'extended_entities' in tweet and 'media' in tweet['extended_entities']:
        media.update([m['media_url'] for m in tweet['extended_entities']['media']])

        videos = [m['video_info'] for m in tweet['extended_entities']['media'] if m['type'] == "video"]
        urls = [n['url'] for m in videos for n in m['variants'] if n['content_type'] == "video/mp4"]
        media.update([x.split("?")[0] for x in urls])

    return media
