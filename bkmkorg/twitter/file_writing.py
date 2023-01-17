
##-- imports
from __future__ import annotations

import pathlib as pl
import datetime
import json
import logging as root_logger
import uuid
from collections import defaultdict
from shutil import copyfile, rmtree
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import bkmkorg.twitter.dfs as DFSU
import networkx as nx
from bkmkorg.twitter.dfs import dfs_chains
from bkmkorg.files.download import download_media
from bkmkorg.twitter.tweet_retrieval import download_tweets
from bkmkorg.twitter.graph import TwitterGraph
from bkmkorg.twitter.data.thread import TwitterOrg
from bkmkorg.twitter.data.todo_list import TweetTodoFile
from bkmkorg.twitter.data.tweet_component import TweetComponents
from bkmkorg.twitter.data.user_summary import TwitterUserSummary
##-- end imports

logging = root_logger.getLogger(__name__)

# TODO could refactor output into template files, ie: jinja.

def construct_component_files(tweet_dir:pl.Path, component_dir:pl.Path, twit=None):
    """ Create intermediate component files of tweet threads
    creates a graph of all tweets in tweet_dir,
    then writes individual connected components to component_dir
    optionally downloading any additional missing tweets as needed if twit is provided
    """

    tweet_graph : TwitterGraph   = TwitterGraph.build(tweet_dir)
    components  : List[Set[Any]] = DFSU.dfs_for_components(tweet_graph)

    logging.info("Creating %s component files\n\tfrom: %s\n\tto: %s", len(components), tweet_dir, component_dir)
    with TweetComponents(component_dir, components) as id_map:
        # create separate component files
        logging.info("Copying to component files")
        # Load each collection of downloaded tweets
        # Note: these are *not* components
        json_files = [x for x in tweet_dir.iterdir() if x.suffix == ".json"]
        for jfile in json_files:
            with open(jfile, 'r') as f:
                data = json.load(f, strict=False)

            # For each tweet loaded, add it into each component file
            for tweet in data:
                # Add tweet to any of its components
                id_str = tweet['id_str']
                id_map.add(tweet, id_str)

                # Add tweet to any component that quotes it
                quoters = tweet_graph.get_quoters(id_str)
                id_map.add(tweet, *quoters)



    if bool(id_map.missing):
        logging.info("Missing: %s", id_map.missing)
        if not download_tweets(twit, tweet_dir, id_map.missing):
            exit()

def construct_user_summaries(component_dir:pl.Path, combined_threads_dir:pl.Path, total_users):
    """ collate threads together by originating user """
    logging.info("Constructing summaries\n\tfrom: %s \n\tto: %s", component_dir, combined_threads_dir)
    user_lookup = total_users
    # Create final orgs, grouped by head user
    components = get_data_files(component_dir, ext=".json")
    for comp in components:
        logging.info("Constructing Summary for: %s", comp)

        # read comp
        with open(comp, 'r') as f:
            data = json.load(f, strict=False)

        if not bool(data):
            logging.warning("No Data found in %s", comp)
            continue

        # Get leaves
        tweets      = {x['id_str'] : x for x in data}
        user_counts = defaultdict(lambda: 0)
        for x in data:
            user_counts[x['user']['id_str']] += 1



        head_user   = max(user_counts.items(), key=lambda x: x[1])[0]
        screen_name = str(head_user)
        if head_user in user_lookup:
            screen_name = user_lookup[head_user]['screen_name']

        logging.debug("Constructing graph")
        graph     = nx.DiGraph()
        quotes    = set()
        roots     = set()
        for tweet in data:
            is_reply      = tweet['in_reply_to_status_id_str'] is not None
            parent_exists = is_reply and tweet['in_reply_to_status_id_str'] not in tweets
            is_quote      = ('quoted_status_id_str' in tweet
                             and tweet['quoted_status_id_str'] is not None)

            match is_reply, parent_exists:
                case True, True:
                    graph.add_edge(tweet['in_reply_to_status_id_str'], tweet['id_str'])
                case _, _:
                    graph.add_node(tweet['id_str'])
                    roots.add(tweet['id_str'])

            if is_quote:
                quotes.add(tweet['quoted_status_id_str'])

        # dfs to get longest chain
        chains = []

        if bool(roots):
            chains = dfs_chains(graph, roots)
        else:
            logging.warning("No Roots were found for component: %s", comp.stem)

        if not bool(chains):
            chains = [list(roots.union(quotes))]

        # Assign main thread as the longest chain
        main_thread = max(chains, key=lambda x: len(x))
        main_set    = set(main_thread)
        main_index  = chains.index(main_thread)

        # assign secondary conversations
        rest = chains[:main_index] + chains[main_index+1:]

        rest         = [x for x in rest if bool(x)]
        # Remove duplications
        cleaned_rest = []
        for thread in rest:
            cleaned = [x for x in thread if x not in main_set]
            cleaned_rest.append(cleaned)
            main_set.update(cleaned)

        # create accessor to summary file
        summary = TwitterUserSummary(screen_name,
                                     combined_threads_dir)

        if summary.user is None:
            if head_user in user_lookup:
                summary.set_user(user_lookup[head_user])
            else:
                summary.set_user(screen_name)


        summary.add_thread(main_thread,
                           cleaned_rest,
                           quotes,
                           tweets)

        # write out user file
        summary.write()



def construct_org_files(combined_threads_dir:pl.Path, org_dir:pl.Path, all_users, todo_tag_bindings:TweetTodoFile):
    logging.info("Constructing org files from: %s \n\tto: %s", combined_threads_dir, org_dir)
    # get all user summary jsons
    user_summaries = get_data_files(combined_threads_dir, ext=".json")

    for summary in user_summaries:
        org_obj = TwitterOrg(summary, org_dir, todo_tag_bindings, all_users)
        if not bool(org_obj):
            logging.warning("User Summary Empty: %s", summary)
            continue

        org_obj.build_threads()
        org_obj.write()
        org_obj.download_media()
