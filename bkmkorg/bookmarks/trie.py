"""
Trie Class for bookmarks
"""

from bkmkorg.util import bookmarkTuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import logging as root_logger
logging = root_logger.getLogger(__name__)


class Trie:
    """ Main Trie Access class """

    def __init__(self, data=None):
        self.root = {}
        self.leaves = []
        self.query_keys = {}
        self.query_key_counts = {}


        if data is not None:
            for x in data:
                self.insert(x)

    def get_tuple_list(self):
        results = []
        for x in self.leaves:
            results += x.get_tuple_list()

        return results

    def __len__(self):
        return len(self.leaves)

    def __str__(self):
        return "Trie: {}, {}".format(len(self), len(self.query_keys))

    __repr__ = __str__


    def insert(self, data):
        """ Insert a bookmark tuple into the trie,
        based on url components """
        assert(isinstance(data, bookmarkTuple))

        if data.name is None:
            logging.debug("No Name: {}".format(data))
            data = bookmarkTuple("Unknown Name", data.url, data.tags)

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
        result = []
        for key, url_pair in self.query_keys.items():
            count = self.query_key_counts[key]
            result.append("** ({}) {}\n  [[{}][original]]\n  [[{}][filtered]]".format(count,
                                                                                      key,
                                                                                      url_pair[0],
                                                                                      url_pair[1]))
        return "\n".join(result)

class Leaf:

    def __init__(self):
        self.data = []

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return "Leaf Group({})".format(len(self))

    __repr__ = __str__

    def get_tuple_list(self):
        return [x.to_tuple() for x in self.data]

    def insert(self, name, url, tags, query_dict, full_path):
        new_leaf = LeafComponent(name, url, tags, query_dict, full_path)
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


class LeafComponent:

    def __init__(self, name, url, tags, query_dict, full_path):
        if not isinstance(query_dict, dict):
            query_dict = {}
        self.name = name
        self.url = url
        self.tags = tags
        self.query = query_dict
        self.full_path = full_path

    def filter_queries(self, query_set):
        for k in list(self.query.keys()):
            if k in query_set:
                del self.query[k]

    def __eq__(self, other):
        if not isinstance(other, LeafComponent):
            return False
        if self.full_path != other.full_path:
            return False
        return True

    def __str__(self):
        return "Leaf({})".format(self.full_path)

    __repr__ = __str__

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
        return bookmarkTuple(self.name,
                             self.reconstruct(),
                             self.tags)
