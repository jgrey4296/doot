#!/usr/bin/env python3
##-- imports
from __future__ import annotations

from os import system
from shlex import quote
import abc
import argparse
import logging as logmod
import pathlib as pl
import subprocess
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from functools import partial
from importlib.resources import files
from re import Pattern
from sys import stderr, stdout
from time import sleep
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

from bkmkorg import DEFAULT_CONFIG, DEFAULT_SECRETS

try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml
##-- end imports

##-- data
data_path    = files(DEFAULT_CONFIG)
data_secrets = data_path / DEFAULT_SECRETS
##-- end data

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Walk through a library directory, and either push to,",
                                                     "or pull from, a tablet to sync the directories"]))
parser.add_argument('--config', default=data_secrets, help="Has a default")
parser.add_argument('--library', required=True, help="The local directory to use")
parser.add_argument('--target',  required=True, help="The remote directory to use")
parser.add_argument('--to-device',   action='store_true')
parser.add_argument('--from-device', action='store_true')
parser.add_argument('--id')
parser.add_argument('--wait', type=int, default=10)
parser.add_argument('--skip-to')
parser.add_argument('--max-depth', type=int)
parser.add_argument('--min-depth', default=1, type=int)
##-- End argparse

##-- Logging
DISPLAY_LEVEL = logmod.INFO
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
file_handler.setFormatter(logmod.Formatter(LOG_FORMAT))

logger.addHandler(console_handler)
logger.addHandler(file_handler)
logging = logger
logging.setLevel(logmod.DEBUG)
##-- End Logging


# reduce priority of processes:
NICE = ["nice", "-n", "10"]

def say(val:str):
    system(f'say -v Moira -r 50 "{val}"')

def esc(path):
    """
    Escape a path for use in adb
    """
    unescaped : str = str(path)
    return quote(unescaped)

def dfs_dir(initial_path, sleep_time, func, skip_to=None, max_depth=None, min_depth=None):
    logging.info("Getting Data Files for: %s", initial_path)
    logging.info("--------------------")
    initial = initial_path if isinstance(initial_path, list) else [initial_path]
    queue = [(x, 1) for x in initial]
    while bool(queue):
        curr_path, depth = queue.pop(0)
        if max_depth and depth >= max_depth:
            continue

        if depth > 1 and skip_to is not None and skip_to != curr_path.name:
            logging.info("Skipping %s", curr_path.name)
            continue
        elif skip_to == curr_path.name:
            skip_to = None

        sub = [(x, depth+1) for x in curr_path.iterdir() if x.is_dir()]
        queue += sub


        if min_depth and depth <= min_depth:
            logging.info("Skipping %s", curr_path.name)
            continue

        logging.info("Running on %s", curr_path.name)
        logging.info("--------------------")
        if func(curr_path.relative_to(initial_path)):
            sleep(sleep_time)

def push_sync(device_id, target, lib, current) -> bool:
    """
    Run an adb push command to sync libdir with the target
    `target` : base path on device
    `lib`    : base path on source
    `current`: current pos relative to `lib`
    """
    logging.info("Pushing: %s\nto     : %s\nBase   : %s", lib, target, current)
    logging.info("--------------------")
    result = subprocess.run(NICE + ["adb",
                             "-t",
                             device_id,
                             "push",
                             "--sync",
                             str(lib / current),
                             str((target / current).parent)],
                            capture_output=True,
                            shell=False)
    if result.returncode != 0:
        logging.warning("Push Failure")
        logging.warning(result.stdout.decode())
        logging.warning(result.stderr.decode())
        raise Exception()
    return True


def pull_sync(device_id, target, lib, current) -> bool:
    """
    Run an adb pull command to sync device with library
    """
    logging.info("Pulling: %s\nto     : %s\ncurrent: %s", target, lib, current)
    logging.info("--------------------")
    # Compare the target and lib using find
    device_files = subprocess.run(NICE + ["adb",
                                   "-t",
                                   device_id,
                                   "shell",
                                   "find",
                                   esc(target/current),
                                   "-type", "f"],
                                  capture_output=True)
    if device_files.returncode != 0:
        logging.warning("Pull Failure: Initial Device Find")
        logging.warning(device_files.stdout.decode())
        logging.warning(device_files.stderr.decode())
        return False

    device_set = { pl.Path(x).relative_to(target) for x in device_files.stdout.decode().split("\n") if x != "" }

    if not (lib/current).exists():
        (lib/current).mkdir()

    local_files = subprocess.run(NICE + ["find",
                                  str(lib/current),
                                  "-type", "f"],
                                 capture_output=True)
    if local_files.returncode != 0:
        logging.warning("Pull Failure: Library Find")
        logging.warning(local_files.stdout.decode())
        logging.warning(local_files.stderr.decode())
        raise Exception()

    local_set = {pl.Path(x).relative_to(lib) for x in local_files.stdout.decode().split("\n") if x != ""}

    missing = device_set - local_set
    logging.info("%s missing from %s", len(missing), lib/current)
    # Then copy missing over
    if not bool(missing):
        return False

    for path in missing:
        assert(not (lib/path).exists())
        if not (lib/path).parent.exists():
            (lib/path).parent.mkdir()

        logging.info("Copying: %s\nTo     : %s", target/path, lib/path)
        result = subprocess.run(NICE + ["adb",
                                "-t",
                                 device_id,
                                "pull",
                                 str(target/path),
                                 str(lib/path)],
                                capture_output=True,
                                shell=False)


        if result.returncode != 0 or not (lib/path).exists():
            logging.warning("Pull Failure: Copy")
            logging.warning(result.stdout.decode())
            logging.warning(result.stderr.decode())
            raise Exception()

    return True

def main():
    logging.info("Starting ADB Unifier")
    args        = parser.parse_args()
    args.config = pl.Path(args.config).expanduser().resolve()

    if not (args.to_device or args.from_device):
        logging.info("Option Missing: --to-device or --from-device")
        exit()

    config = toml.load(args.config)
    # device_id = "{}:{}".format(config['ADB']['ipaddr'], config['ADB']['PORT'])
    device_id = args.id
    # Walk the library directory
    if args.to_device:
        func = push_sync
    elif args.from_device:
        func = pull_sync
    else:
        raise Exception()

    lib_path    = pl.Path(args.library).expanduser().resolve()
    target_path = pl.Path(config['ADB']['sdcard']) /  args.target

    # Curry the args which won't change
    partial_func = partial(func,
                           device_id,
                           target_path,
                           lib_path)


    logging.info("DFS for: %s\nto: %s\non depth: %s < n < %s", lib_path, target_path, args.min_depth, args.max_depth)
    # Run the walk
    try:
        dfs_dir(lib_path,
                args.wait,
                partial_func,
                skip_to=args.skip_to,
                min_depth=args.min_depth,
                max_depth=args.max_depth)
        say("Finished ADB Backup")
    except Exception as err:
        say("DFS Failure")
        logging.warning(err)

##-- ifmain
if __name__ == '__main__':
    main()


##-- end ifmain
