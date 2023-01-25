#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from re import Pattern, compile
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

user_head_str   : Final[str]     = r"^\* {}'s Threads"
thread_start_re : Final[Pattern] = compile(r"^\*\* Thread:")
short_url_re    : Final[Pattern] = compile(r"^([^\[]*)(https?://t\.co/.+)$")
file_uri_re     : Final[Pattern] = compile(r"(.*?)(file:\./)(.+)$")
link_re         : Final[Pattern] = compile(r"(.*?)\[\[(https://t\.co/.+?)\](\[.+?\])?\](.*)$")
fname_extract_re: Final[Pattern] = compile(r"(.+)(_\d+)?.org")

def build_threader(output, base_name, pattern):
    count = 1

    def next_thread_context():
        nonlocal count
        logging.info("Found Thread: %s", count)
        new_thread_name = output / pattern.format(base_name, count)
        count += 1
        return new_thread_name

    return next_thread_context

def process_file(path):
    """
    Given a path to /path/to/library/blah.org
    Split it into separate threads in its own subdir
    """
    assert(path.exists() and path.is_file())
    process_pattern(path.parent / path.stem)

def process_pattern(target):
    """
    Given a path like /path/to/library/blah
    Look for the glob blah*.org in /path/to/library
    and create a collected directory of threads
    """
    directory = target.parent
    base_name = target.stem
    output    = directory / f"{base_name}_collected"

    if output.exists() and bool(list(output.glob("*.org"))):
        raise Exception(f"Output Dir can't Exist: {output}")

    if not bool(directory.glob(f"{base_name}*.org")):
        raise Exception("No Applicable Files to Glob")

    # Applicable Files, and output dir
    if not output.exists():
        output.mkdir()

    logging.info("Building Master File for: -------------------- %s", base_name)
    globbed = list(directory.glob(f"{base_name}*.org"))
    logging.info("Found %s orgs to collect from.", len(globbed))
    with open(output / "master_file.org", 'a') as master:
        for fpath in globbed:
            with open(fpath, 'r') as f:
                master.write(f.read())
            master.write("\n\n")

    # Then Read the master file
    # and create separate thread files
    logging.info(f"Building Separate Threads from Master File")
    thread_maker     = build_threader(output, base_name, "{}_thread_{}.org")
    user_head        = output / f"{base_name}_details.org"
    user_head_re     = compile(user_head_str.format(base_name))
    in_thread        = False
    curr_thread_file = user_head
    count            = 0
    with open(output / 'master_file.org', 'r') as master:
        for line in master:
            if thread_start_re.match(line):
                in_thread = True
                curr_thread_file = thread_maker()
                count += 1
            elif user_head_re.match(line):
                in_thread = False
                curr_thread_file = user_head
            #endif

            line = process_short_url(line, in_thread)
            line = process_file_uri(line)
            line = process_link(line)

            with open(curr_thread_file, 'a') as f:
                f.write(line)

    logging.info("Completed, built %s thread files", count)

def process_link(line):
    link_matched = link_re.match(line)
    if link_matched:
        res = requests.head(link_matched[2])
        if res.is_redirect:
            url       = res.headers['location']
            link_name = link_matched[3] if link_matched[3] is not None else ""
            line      = f"{link_matched[1]}[[{url}]{link_name}]{link_matched[4]}\n"

    return line

def process_short_url(line, in_thread):
    url_matched = short_url_re.match(line)
    if url_matched:
        res = requests.head(url_matched[2])
        if res.is_redirect:
            url = res.headers['location']
            if in_thread:
                line = f"{url_matched[1]}\n\n{url_matched[2]}\n{url}\n"
            else:
                line = f"{url_matched[1]}{url_matched[2]} {url}"

    return line

def process_file_uri(line):
    file_matched = file_uri_re.match(line)
    if file_matched:
        line = f"{file_matched[1]}file:../{file_matched[3]}\n"

    return line
