"""
Automate twitter archiving

"""
import logging as root_logger
import json
import networkx as nx
import requests
import configparser
import twitter
import argparse
import uuid
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir, mkdir
import re

PERMALINK_RE = re.compile("\[.+?/status/(\d+)\]\]")
GROUP_AMNT = 100

def dfs_directory(*dirs, filetype=".org"):
    found = []
    queue = [] + list(dirs)

    while bool(queue):
        current = queue.pop(0)
        # Add files
        found += [join(current, x) for x in listdir(current) if isfile(join(current, x)) and splitext(x)[1] == filetype]
        # Continue for directories
        queue += [join(current,x) for x in listdir(current) if isdir(join(current, x)) and x != ".git"]

    return found

def extract_tweet_ids_from_file(the_file, simple=False):
    use_regex = PERMALINK_RE
    if simple:
        use_regex = re.compile("/status/(\d+)")

    exists(the_file)
    with open(the_file, 'r') as f:
        lines = f.readlines()

    # grep file lines for permalinks
    results = set()
    for line in lines:
        match = use_regex.search(line)
        if match is not None:
            results.add(match[1])

    return results

def extract_tweet_ids_from_json(the_file):
    try:
        with open(the_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logging.info("File issue: {}".format(the_file))
        raise e

    ids = [x['id_str'] for x in data]
    return ids

def extract_media_and_users_from_json(the_file):
    try:
        with open(the_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logging.info("File issue: {}".format(the_file))
        raise e

    ids = set()
    media = set()
    for x in data:
        if 'media' in x:
            media.update([m['media_url'] for m in x['media']])

            videos = [m['video_info'] for m in x['media'] if m['type'] == "video"]
            urls = [n['url'] for m in videos for n in m['variants'] if n['content_type'] == "video/mp4"]
            media.update([x.split("?")[0] for x in urls])

        if 'in_reply_to_user_id' in x:
            ids.add(x['in_reply_to_user_id'])

        if "quoted_status" in x:
            ids.add(x['quoted_status']['user']['id_str'])

        ids.add(x['user']['id_str'])


    return ids, media

def get_all_tweet_ids(*the_dirs):
    tweet_ids = set()

    for a_dir in the_dirs:
        if isfile(a_dir):
            with open(a_dir, 'r') as f:
                tweet_ids.update([x.strip() for x in f.readlines()])

        elif isdir(a_dir):
            all_files = dfs_directory(*the_dirs)
            for x in all_files:
                tweet_ids.update(extract_tweet_ids_from_file(x))

    return tweet_ids

def dfs_edge(graph, edge):
    found = set()
    queue = [edge]

    while bool(queue):
        current = queue.pop(0)
        l, r = current
        if l in found and r in found:
            continue

        found.add(l)
        found.add(r)
        queue += [(l, x) for x in graph.adj[l] if graph.adj[l][x]['type'] != "quote"]
        queue += [(r, x) for x in graph.adj[r] if graph.adj[r][x]['type'] != "quote"]

    return found




if __name__ == "__main__":
    # Setup root_logger:
    LOGLEVEL = root_logger.DEBUG
    LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
    root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

    console = root_logger.StreamHandler()
    console.setLevel(root_logger.INFO)
    root_logger.getLogger('').addHandler(console)
    logging = root_logger.getLogger(__name__)
    logging.info("Automated Twitter Archiver")
    ####################
    # Setup argparser
    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join([""]))
    parser.add_argument('--config', default="secrets.config")
    parser.add_argument('--library', action="append")
    parser.add_argument('--target')
    parser.add_argument('--media')
    parser.add_argument('--json')
    parser.add_argument('--export')

    args = parser.parse_args()
    args.config = abspath(expanduser(args.config))
    if args.library is not None:
        args.library = [abspath(expanduser(x)) for x in args.library]
    else:
        args.library = []

    if args.export is not None:
        args.export = abspath(expanduser(args.export))
    else:
        args.target = abspath(expanduser(args.target))
        args.json = abspath(expanduser(args.json))
        args.media = abspath(expanduser(args.media))

    logging.info("Library: {}".format(args.library))
    logging.info("Config: {}".format(args.config))
    logging.info("Json Directory: {}".format(args.json))
    logging.info("Target: {}".format(args.target))
    ####################
    # Read Configs
    config = configparser.ConfigParser()
    with open(args.config, 'r') as f:
         config.read_file(f)
    ####################
    # INIT twitter object
    logging.info("Initialising Twitter")
    twit = twitter.Api(consumer_key=config['DEFAULT']['consumerKey'],
                       consumer_secret=config['DEFAULT']['consumerSecret'],
                       access_token_key=config['DEFAULT']['accessToken'],
                       access_token_secret=config['DEFAULT']['accessSecret'],
                       sleep_on_rate_limit=config['DEFAULT']['sleep'],
                       tweet_mode='extended')

    # Extract all tweet id's from library
    logging.info("Getting Library Tweet Details")
    library_tweet_ids = get_all_tweet_ids(*args.library)
    logging.info("Found {} library tweets".format(len(library_tweet_ids)))

    if args.export is not None:
        logging.info("Exporting to: {}".format(args.export))
        with open(args.export, 'w') as f:
            f.write("\n".join(library_tweet_ids))
        exit()

    # read file of tweet id's
    logging.info("Getting Target Tweet ids")
    source_ids = set(extract_tweet_ids_from_file(args.target, simple=True))
    logging.info("Found {} source ids".format(len(source_ids)))
    # read tweet id's from json dir files
    if not exists(args.json):
        logging.info("Creating Json Directory")
        mkdir(args.json)

    logging.info("Reading existing tweet jsons")
    json_files = [join(args.json, x) for x in listdir(args.json) if splitext(x)[1] == ".json" and split(x)[1] != "users.json"]
    json_ids = set()
    for jfile in json_files:
        json_ids.update(extract_tweet_ids_from_json(jfile))

    logging.info("Found {} exiting tweet ids in jsons".format(len(json_ids)))
    # remove tweet id's already in library
    logging.info("Removing existing tweets from queue")
    remaining = (source_ids - library_tweet_ids) - json_ids
    logging.info("Remaining ids to process: {}".format(len(remaining)))
    queue = list(remaining)
    # Loop:
    while bool(queue):
        logging.info("Queue loop: {}".format(len(queue)))
        # Pop group amount:
        current = set(queue[:GROUP_AMNT])
        current -= json_ids
        current = list(current)
        queue = queue[GROUP_AMNT:]

        try:
            ## download tweets
            results = twit.GetStatuses(current, trim_user=True)
            # add results to results dir
            new_json_file = join(args.json, "{}.json".format(uuid.uuid1()))
            assert(not exists(new_json_file))
            with open(new_json_file, 'w') as f:
                as_json = "[{}]".format(",".join([x.AsJsonString() for x in results]))
                f.write(as_json)

            # update ids
            json_ids.update([x.id_str for x in results])

            # Add new referenced ids:
            for x in results:
                if x.in_reply_to_status_id is not None:
                    queue.append(str(x.in_reply_to_status_id))
                if x.quoted_status_id_str is not None:
                    queue.append(x.quoted_status_id_str)

        except Exception as e:
            # handle failure
            breakpoint()
            logging.warning("Exception")



    # --------------------
    # Finished downloading, now construct orgs
    logging.info("Finished Retrieval")


    # Now create threads
    logging.info("Assembling Threads")
    json_files = [join(args.json, x) for x in listdir(args.json) if splitext(x)[1] == ".json" and split(x)[1] != "users.json"]
    di_graph = nx.DiGraph()
    for jfile in json_files:
        # load in each json,
        with open(jfile, 'r') as f:
            data = json.load(f)

        # construct connection graph
        for entry in data:
            # get tweet id, reply_id, quote_id
            tweet_id = entry['id_str']
            di_graph.add_node(tweet_id, source_file=jfile)

            if 'in_reply_to_status_id' in entry:
                # link tweets
                di_graph.add_edge(tweet_id,
                               str(entry['in_reply_to_status_id']),
                               type="reply")

            if 'quoted_status_id_str' in entry:
                di_graph.add_edge(entry['quoted_status_id_str'],
                                  tweet_id,
                                  type="quote")

    # Convert to undirected graph
    graph = nx.Graph(di_graph)

    # DFS for components
    components = []
    edge_set = set(graph.edges)
    discovered = set()
    while bool(edge_set):
        current = edge_set.pop()
        if current[0] in discovered and current[1] in discovered:
            continue
        # Get connected edges
        connected_ids = dfs_edge(graph, current)
        components.append(connected_ids)
        discovered.update(connected_ids)

    logging.info("Found {} components".format(len(components)))

    logging.info("Creating Components")
    id_map = {}
    for comp_set in components:
        # Then to each id in that component:
        component_filename = join(args.json, "component_{}.json".format(uuid.uuid1()))
        assert(not exists(component_filename))
        id_map.update({x : component_filename for x in comp_set})


    # create separate component files
    logging.info("Copying to component files")
    for jfile in json_files:
        with open(jfile, 'r') as f:
            data = json.load(f)

        for tweet in data:
            # Add tweet to any of its components
            id_str = tweet['id_str']
            if id_str in id_map:
                component_filename = id_map[id_str]

                is_fresh = not exists(component_filename)
                with open(component_filename, 'a') as f:
                    if is_fresh:
                        f.write("[")
                    else:
                        f.write(",")
                    f.write(json.dumps(tweet))

            # Add tweet to any component that quotes it
            quoter_edges = [x for x in di_graph[id_str] if di_graph[id_str][x] == "quote"]
            for quoter_id in quoter_edges:
                component_filename = id_map[quoter_id]
                is_fresh = not exists(component_filename)
                with open(component_filename, 'a') as f:
                    if is_fresh:
                        f.write("[")
                    else:
                        f.write(",")
                    f.write(json.dumps(tweet))

    # After every file is finished, add a final ]
    for component_fname in set(id_map.values()):
        if not exists(component_fname):
            continue
        with open(component_fname, 'a') as f:
            f.write(']')


    # Get all user ids and media urls
    logging.info("Getting media urls")
    json_files = [join(args.json, x) for x in listdir(args.json) if splitext(x)[1] == ".json" and split(x)[1] != "users.json"]
    users = set()
    media = set()
    for f in json_files:
        tusers, tmedia = extract_media_and_users_from_json(f)
        users.update(tusers)
        media.update(tmedia)

    logging.info("Found {} unique media files".format(len(media)))
    logging.info("Found {} unique users".format(len(users)))

    # download media
    logging.info("Downloading media")
    if not exists(args.media):
        mkdir(args.media)

    scaler = int(len(media) / 100)
    count = 0
    for i,x in enumerate(media):
        if i % scaler == 0:
            logging.info("{}/100".format(int(i/scaler)))
        filename = split(x)[1]
        if exists(join(args.media, filename)):
            continue

        request = requests.get(x)
        with open(join(args.media, filename), 'wb') as f:
            f.write(request.content)

    # Get all user identities
    logging.info("Getting user identities")
    total_users = []
    if exists(join(args.json, "users.json")):
        with open(join(args.json, "users.json")) as f:
            total_users += json.load(f)

        users -= set([x['id_str'] for x in total_users])
    logging.info("Already retrieved {}, {} remaining".format(len(total_users), len(users)))
    user_queue = list(users)
    while bool(user_queue):
        current = user_queue[:100]
        user_queue = user_queue[100:]

        data = twit.UsersLookup(user_id=current)
        total_users += [json.loads(x.AsJsonString()) for x in data]


    with open(join(args.json, "users.json"), 'w') as f:
        json.dump(total_users, f)

    # Create final orgs, grouped by head user
    # for each component file:
    ## insert tweets in order

    ### time, user name, content, relative link link to images, expanded urls

    ## insert in reply to and references
