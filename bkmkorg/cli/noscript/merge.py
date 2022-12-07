#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import pathlib as pl
import abc
import argparse
import json
import logging as logmod
from dataclasses import InitVar, dataclass, field
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from collections import defaultdict

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
DISPLAY_LEVEL = logmod.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
LOG_FORMAT    = "%(asctime)s | %(levelname)8s | %(message)s"
FILE_MODE     = "w"
STREAM_TARGET = stderr # or stdout

logger          = logmod.getLogger(__name__)
console_handler = logmod.StreamHandler(STREAM_TARGET)
file_handler    = logmod.FileHandler(LOG_FILE_NAME, mode=FILE_MODE)

console_handler.setLevel(DISPLAY_LEVEL)
# console_handler.setFormatter(logmod.Formatter(LOG_FORMAT))
file_handler.setLevel(logmod.DEBUG)
# file_handler.setFormatter(logmod.Formatter(LOG_FORMAT))

logger.addHandler(console_handler)
logger.addHandler(file_handler)
logging = logger
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))
parser.add_argument('-t', '--target', action="append", required=True)
parser.add_argument('-o', '--output', default="~/Desktop/noscript.json")
parser.add_argument('--override', action="store_true")
##-- end argparse

def merge_json(target, source, key):

    queue = [(target, source, key)]

    while bool(queue):
        current = queue.pop()
        print(f"Merging: {current[2]}")
        targ = current[0][current[2]]
        sour = current[1][current[2]]

        match (targ, sour):
            case dict(), dict():
                for key in sour.keys():
                    if key not in targ:
                        targ[key] = sour[key]
                    else:
                        queue += [(targ, sour, key)]
            case list(), list():
                print(f"Merging Lists: {len(targ)} : {len(sour)}")
                now_set = set(targ)
                now_set.update(sour)
                print(f"Updated Length: {len(now_set)}")
                targ.clear()
                targ.extend(now_set)
            case bool(), bool() if targ != sour:
                print(f"{current[2]} Conflict: {targ}, {sour}")
                result = input(f"Enter for {targ}, else {sour}")
                if not bool(result):
                    current[0][current[2]] = targ
                else:
                    current[0][current[2]] = sour
            case bool(), bool():
                pass



def main():
    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    args.target = [pl.Path(x).expanduser().resolve() for x in args.target]

    full_targets = []
    for target in args.target:
        if not target.is_dir():
            assert(target.suffix == ".json")
            full_targets.append(target)
            continue

        assert(target.is_dir())
        full_targets += [x for x in target.iterdir() if x.suffix == ".json"]

    args.target = full_targets

    assert(args.output.suffix == ".json")
    assert(args.override or not args.output.exists()), "--override or specify a non-existing output"

    final = defaultdict(lambda: {})

    # load jsons
    for target in args.target:
        print(f"Loading {target}")
        with open(target, 'r') as f:
            data = json.load(f)

        for key in data:
            merge_json(final, data, key)


    for site in final['policy']['sites']['trusted']:
        assert(site not in final['policy']['sites']['untrusted']), site

    print("Final Sizes: ")
    print(f"  Trusted Sites: {len(final['policy']['sites']['trusted'])}")
    print(f"UnTrusted Sites: {len(final['policy']['sites']['untrusted'])}")

    # write out merged json
    with open(args.output, 'w') as f:
        json.dump(final, f, indent=4, sort_keys=True, ensure_ascii=False)



##-- ifmain
if __name__ == '__main__':
    main()

##-- end ifmain
