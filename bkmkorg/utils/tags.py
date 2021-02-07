#!/usr/bin/env python3

"""
Tagset Utilities

"""
import logging as root_logger
logging = root_logger.getLogger(__name__)

import networkx as nx
import regex
import regex as re


def extract_tags_from_bibtex(db, the_graph=None):
    logging.info("Processing Bibtex: {}".format(len(db.entries)))
    if the_graph is None:
        the_graph = nx.Graph()

    proportion = int(len(db.entries) / 10)
    count = 0
    for i, entry in enumerate(db.entries):
        if i % proportion == 0:
            logging.info("{}/10 Complete".format(count))
            count += 1

        #get tags
        e_tags = entry['tags']
        remaining = list(e_tags)

        for x in e_tags:
            if x not in the_graph:
                the_graph.add_node(x, count=0)
            the_graph[x]['count'] += 1

            remaining.remove(x)
            edges_to_increment = [(x,y) for y in remaining]
            for u,v in edges_to_increment:
                if not the_graph.has_edge(u,v):
                    the_graph.add_edge(u,v, weight=0)
                the_graph[u][v]['weight'] += 1

    return the_graph



def extract_tags_from_org_files(org_files, the_graph=None, tag_regex="^\*\*\s+.+?\s+:(\S+):$"):
    logging.info("Extracting data from orgs")
    if the_graph is None:
        the_graph = nx.Graph()
    ORG_TAG_REGEX = regex.compile(tag_regex)

    for org in org_files:
        #read
        text = []
        with open(org,'r') as f:
            text = f.readlines()

        #line by line
        for line in text:
            tags = ORG_TAG_REGEX.findall(line)
            individual_tags = []
            if not bool(tags):
                continue

            individual_tags = [x for x in tags[0].split(':') if x != '']
            remaining = individual_tags[:]


            #Add to dict:
            for tag in individual_tags:
                if tag not in the_graph:
                    the_graph.add_node(tag, count=0)
                the_graph[tag]['count'] += 1

                remaining.remove(tag)
                edges_to_increment = [(tag,y) for y in remaining]
                for u,v in edges_to_increment:
                    if not the_graph.has_edge(u,v):
                        the_graph.add_edge(u,v, weight=0)
                    the_graph[u][v]['weight'] += 1

    return the_graph


def extract_tags_from_html_files(html_files, the_graph=None):
    logging.info("Extracting data from htmls")
    if the_graph is None:
        the_graph = nx.Graph()

    for html in html_files:
        bkmks = open_and_extract_bookmarks(html)
        for bkmk in bkmks:
            remaining = list(bkmk.tags)
            for tag in bkmk.tags:
                if tag not in the_graph:
                    the_graph.add_node(tag, count=0)
                the_graph[tag]['count'] += 1

                remaining.remove(tag)
                edges_to_increment = [(tag,y) for y in remaining]
                for u,v in edges_to_increment:
                    if not the_graph.has_edge(u,v):
                        the_graph.add_edge(u,v, weight=0)
                    the_graph[u][v]['weight'] += 1

    return the_graph
def collect_tag_substitutions(targets):
    """ DFS targets, get tags, """
    logging.info("Collecting Tags")
    tag_substitutor = {}
    remaining = targets[:]
    processed = set([])
    while bool(remaining):
        current = remaining.pop(0)
        if current in processed:
            continue
        if isfile(current):
            ext = splitext(current)[1]
            if ext == ".tags":
                #read raw tags
                tag_substitutor.update(read_raw_tags(current))
            elif ext == ".org":
                #read_org file
                tag_substitutor.update(read_org_tags(current))

            processed.add(current)
        else:
            assert(isdir(current))
            subdirs = [join(current, x) for x in listdir(current)]
            remaining += subdirs


    return tag_substitutor

def combine_all_tags(dict_array):
    logging.info("Combining tags")
    all_tags = {}

    for tag_dict in dict_array:
        for tag,count in tag_dict.items():
            if tag not in all_tags:
                all_tags[tag] = 0
            all_tags[tag] += count

    return all_tags




def write_tags(all_tags, output_target):
    tag_str = ["{} : {}".format(k, v) for k, v in all_tags.items()]
    with open("{}.tags".format(output_target), 'w') as f:
        logging.info("Writing Tag Counts")
        f.write("\n".join(tag_str))







