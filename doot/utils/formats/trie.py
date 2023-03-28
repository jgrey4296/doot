"""
Trie Class for bookmarks
"""
##-- imports
from __future__ import annotations

import logging as logmod
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from doot.utils.formats.bookmarks import Bookmark
##-- end imports

logging = logmod.getLogger(__name__)

@dataclass
class Trie:
    """ Main Trie Access class """
    data : InitVar[List[Any]] = field(default=None)

    root             : Dict[Any, Any] = field(init=False, default_factory=dict)
    leaves           : List[Any]      = field(init=False, default_factory=list)
    query_keys       : Dict[Any, Any] = field(init=False, default_factory=dict)
    query_key_counts : Dict[Any, int] = field(init=False, default_factory=dict)

    __repr__ = __str__

    def __post_init__(self, data=None):
        if data is not None:
            for x in data:
                self.insert(x)

    def __len__(self):
        return len(self.leaves)

    def __str__(self):
        return "Trie: {}, {}".format(len(self), len(self.query_keys))

    def get_tuple_list(self):
        results = []
        for x in self.leaves:
            results += x.get_tuple_list()

        return results

    def insert(self, data):
        """ Insert a bookmark into the trie,
        based on url components """
        assert(isinstance(data, Bookmark))

        #Get components of the url
        p_url = urlparse(data.url)
        trie_path = [p_url.scheme, p_url.netloc] + p_url.path.split('/')
        f_trie_path = [x for x in trie_path if x]

        query = parse_qs(p_url.query)

        #find the leaf
        current_child = self.root
        for x in f_trie_path:
            if x not in current_child:
                current_child[x] = {}
            current_child = current_child[x]

        #insert into the leaf, merging tag sets
        if '__leaf' not in current_child:
            new_leaf = Leaf()
            current_child['__leaf'] = new_leaf
            self.leaves.append(new_leaf)

        leaf = current_child['__leaf']
        leaf_node = leaf.insert(data.name, p_url, data.tags, query, data.url)

        for k in query.keys():
            if k not in self.query_keys:
                self.query_keys[k] = (data.url, leaf_node.reconstruct(k))
                self.query_key_counts[k] = 0
            self.query_key_counts[k] += 1

    def filter_queries(self, query_set):
        for x in self.leaves:
            x.filter_queries(query_set)

    def org_format_queries(self):
        """
        Output a list of org links, with original URLs,
        and URL's minus a query parameter.
        Used to find out which parameters can be filtered from links
        """
        result = []
        for key, url_pair in self.query_keys.items():
            count = self.query_key_counts[key]
            result.append("** ({}) {}\n  [[{}][original]]\n  [[{}][filtered]]".format(count,
                                                                                      key,
                                                                                      url_pair[0],
                                                                                      url_pair[1]))
        return "\n".join(result)

@dataclass
class Leaf:

    data : List[Any] = field(default_factory=list)

    __repr__ = __str__

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return "Leaf Group({})".format(len(self))

    def get_tuple_list(self):
        return [x.to_tuple() for x in self.data]

    def insert(self, name, url, tags, query_dict, full_path):
        new_leaf = LeafComponent(name, url, tags, full_path, query_dict)
        if new_leaf in self.data:
            logging.info("Merging tags")
            existing = self.data.index(new_leaf)
            existing.tags.update(tags)
            return existing
        else:
            self.data.append(new_leaf)
            return new_leaf

    def filter_queries(self, query_set):
        for x in self.data:
            x.filter_queries(query_set)

@dataclass
class LeafComponent:

    name      : str            = field()
    url       : str            = field()
    tags      : List[str]      = field()
    full_path : str            = field()
    query     : Dict[Any, Any] = field(default_factory=dict)

    __repr__ = __str__

    def __eq__(self, other):
        if not isinstance(other, LeafComponent):
            return False
        if self.full_path != other.full_path:
            return False
        return True

    def __str__(self):
        return "Leaf({})".format(self.full_path)

    def filter_queries(self, query_set):
        for k in list(self.query.keys()):
            if k in query_set:
                del self.query[k]

    def reconstruct(self, key=None):
        copied = {}
        copied.update(self.query)
        if key in copied:
            del copied[key]
        query_str = urlencode(copied, True)
        full_path = urlunparse((self.url.scheme,
                                self.url.netloc,
                                self.url.path,
                                self.url.params,
                                query_str,
                                self.url.fragment))
        return full_path

    def to_tuple(self):
        return Bookmark(self.reconstruct(),
                        self.tags,
                        name=self.name)
