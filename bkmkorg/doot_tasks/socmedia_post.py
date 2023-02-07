#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from random import choice
import doot
from doot import tasker, task_mixins
from bkmkorg.apis.mastodon import MastodonMixin
from bkmkorg.apis.twitter import TwitterMixin
from bkmkorg.bibtex.load_save import BibLoadSaveMixin
from bkmkorg.bibtex.clean import BibPathCleanMixin, BibFieldCleanMixin
from bkmkorg.bibtex import utils as bib_utils

pl_expand           : Final = lambda x: pl.Path(x).expanduser().resolve()

MAX_ATTEMPTS       : Final = doot.config.on_fail(20, int).tool.doot.bibtex.max_attempts()
tweet_size         : Final = doot.config.on_fail(250, int).tool.doot.twitter.tweet_size()
toot_size          : Final = doot.config.on_fail(250, int).tool.doot.mastodon.toot_size()


conversion_args     : Final = doot.config.on_fail(["-define", "jpeg:extent=4800KB"], list).tool.doot.photo.convert_args()
required_keys       : Final = doot.config.on_fail(["year", "author", "title", "tags"], list).tool.doot.bibtex.required_keys()
one_of_keys         : Final = doot.config.on_fail(["doi", "url", "isbn"], list).tool.doot.bibtex.one_of_keys()

class BibPoster(tasker.DootTasker, MastodonMixin, TwitterMixin, BibLoadSaveMixin, BibPathCleanMixin, BibFieldCleanMixin):
    """
    select an entry from bibtex library, and tweet/toot
    """

    def __init__(self, name="post::bib", locs=None):
        super().__init__(name, locs)
        self.mastodon        = None
        self.twitter         = None
        self.db              = None
        self.blacklist       = set()
        self.already_tweeted = set()
        assert(self.locs.secrets)
        assert(self.locs.bib_blacklist)
        assert(self.locs.bib_success)
        assert(self.locs.bib_fail)
        assert(self.locs.bibtex)


    def setup_detail(self, task):
        task.update({
            "actions": [
                (self.setup_mastodon, [self.locs.secrets]),
                (self.setup_twitter,  [self.locs.secrets]),
                self.load_records,
            ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions": [
                self.select_bibtex_file,
                self.load_bibtex_file,
                self.select_entry,
                self.format_tweet,
                self.post_tweet,
                self.post_toot,
                self.record_result,
            ],
            "teardown": [self.write_blacklist]
        })
        return task

    def load_records(self):
        if self.locs.bib_blacklist.exists():
            self.blacklist       = {x for x in self.locs.bib_blacklist.read_text().split("\n")}
        if self.locs.bib_success.exists():
            self.already_tweeted = {x for x in self.locs.bib_success.read_text().split("\n")}

    def select_bibtex_file(self) -> pl.Path:
        print("Selecting bibtex")
        # load blacklist
        bibs      = {x for x in self.locs.bibtex.iterdir() if x.suffix == ".bib"}
        filtered  = [x for x in bibs if x.stem not in self.blacklist]

        if not bool(filtered):
            return False
        selected = choice(filtered)
        return { 'selected': [str(selected)] }

    def load_bibtex_file(self, task):
        self.db = self.bc_load_db(task.values['selected'], fn=self.process_entry)

    def process_entry(self, entry):
        self.bc_to_unicode(entry)
        self.bc_split_names(entry)
        self.bc_tag_split(entry)

        return entry

    def select_entry(self, task):
        print("Selecting Entry")
        if not bool(self.db.entries):
            return False

        for x in range(MAX_ATTEMPTS):
            poss_entry         = choice(self.db.entries)
            has_keys           = all([x in poss_entry for x in required_keys])
            one_of             = any([x in poss_entry for x in one_of_keys])
            not_tweeted_before = poss_entry['ID'] not in self.already_tweeted

            if has_keys and one_of and not_tweeted_before:
                return { 'entry_id': poss_entry['ID'] }

        self.maybe_blacklist_files(task.values['selected'])

        return False

    def format_tweet(self, task):
        print("Formatting Entry")
        entry = self.db.entries_dict.get(task.values['entry_id'], None)
        assert(entry is not None)
        assert("__split_names" in entry)
        assert("__as_unicode" in entry)
        assert("__tags" in entry)

        people = []
        match entry:
            case { "__authors" : [*authors]}:
                people += authors
            case { "__editors" : [*editors]}:
                people += editors
            case _:
                raise Exception("No author or editor for entry: %s", entry)

        author = bib_utils.names_to_str(people, entry)

        if len(author) > 30:
            author = f"{author[:30]}..."

        result = []
        result.append(entry['title'])
        result.append(f"({entry['year']}) : {author}")
        match entry:
            case { "doi": doi }:
                result.append(f"DOI: https://doi.org/{doi}")
            case { "url": url }:
                result.append(f"url: {url}")
            case { "isbn": isbn }:
                result.append(f"isbn: {isbn}")
            case _:
                logging.warning("Bad Entry: %s", entry['ID'])
                return False

        tags_list   = [f"#{x}" for x in entry['__tags']]
        tags_to_add = []
        base_len    = sum(len(x) for x in result)
        max_size    = max(toot_size, tweet_size) - len("#my_bibtex") - 10
        while bool(tags_list) and base_len <= max_size:
            tag       = tags_list.pop(0)
            base_len += len(tag)
            tags_to_add.append(tag)

        tags_to_add.append("#my_bibtex")

        base_tweet = "\n".join(result)
        tags_line  = " ".join(tags_to_add)

        return { 'msg' :  f"{base_tweet}\n{tags_line}" }

    def record_result(self, task):
        match task.values:
            case { "twitter_result" : True, "toot_result": True, "entry_id": entry_id }:
                with open(self.locs.bib_success, 'a') as f:
                    f.write(f"\n{entry_id}")
            case { "twitter_result" : False, "toot_result": True, "entry_id": entry_id }:
                print("Only Toot Posted")
            case { "twitter_result" : True, "toot_result": True, "entry_id": entry_id }:
                print("Only Tweet Posted")
            case { "entry_id": entry_id }:
                with open(self.locs.bib_fail, 'a') as f:
                    f.write(f"\n{entry_id}")


    def maybe_blacklist_files(self, files:list[pl.Path]):
        has_fields       = lambda poss_entry: any([x in poss_entry for x in one_of_keys])
        not_tweeted_yet  = lambda poss_entry: poss_entry['ID'] not in self.already_tweeted
        sufficient_entry = lambda entry: has_fields(entry) and not_tweeted_yet(entry)

        assert(all([pl.Path(fstr).stem not in self.blacklist for fstr in files]))
        if any([sufficient_entry(x) for x in self.db.entries]):
            return

        logging.info("Bibtex failed check, blacklisting: %s", files)
        self.blacklist.update(pl.Path(fpath).stem for fpath in files)

    def write_blacklist(self):
        self.locs.bib_blacklist.write_text("\n".join(self.blacklist))

class ImagePoster(tasker.DootTasker, MastodonMixin, TwitterMixin, task_mixins.ActionsMixin):
    """
    Select an image from the whitelist, and tweet/toot
    """

    def __init__(self, name="post::image", locs=None):
        super().__init__(name, locs)
        self.whitelist = set()
        assert(self.locs.secrets)
        assert(self.locs.image_whitelist)

    def setup_detail(self, task):
        task.update({
            "actions": [
                (self.setup_mastodon, [self.locs.secrets]),
                (self.setup_twitter,  [self.locs.secrets]),
                self.load_image_lists,

            ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions": [
                self.select_file,
                self.post_mastodon_image,
                self.post_twitter_image,
            ],
        })
        return task

    def load_image_lists(self):
        self.whitelist.update({x for x in self.locs.image_whitelist.read_text().split("\n")})

    def select_file(self):
        selected = choice(list(self.whitelist))
        if "cora" in str(selected).lower():
            msg  = "Cora"
            desc = "My Cat, Cora"
        elif "kira" in str(selected).lower():
            msg  = "Kira"
            desc = "My Cat, Kira"
        else:
            raise Exception("Unexpected Image", selected)

        return {'image': selected, 'msg': msg, "desc": desc}
