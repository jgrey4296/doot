#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import abc
import argparse
import logging as logmod
import pathlib as pl
import subprocess
from configparser import ConfigParser
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
##-- end imports

##-- data
data_path    = files(f"bkmkorg.{DEFAULT_CONFIG}")
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
parser.add_argument('--depthskip', default=1, type=int)
parser.add_argument('--id')
parser.add_argument('--wait', type=int, default=10)
parser.add_argument('--skip-to')
parser.add_argument('--max-depth', type=int)
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

def say(val:str):
    system(f'say -v Moira -r 50 "{val}"')

# TODO use asyncio for subprocess control

def skip_depth_under(path, curr, depth=1):
    up_by_depth = path/curr
    for x in range(depth):
        up_by_depth = up_by_depth.parent

    return up_by_depth < path

def dfs_dir(initial_path, sleep_time, func, skip_to=None, max_depth=None):
    logging.info("Getting Data Files for: %s", initial_path)
    logging.info("--------------------")
    initial = initial_path if isinstance(initial_path, list) else [initial_path]
    queue = [(x, 1) for x in initial]
    while bool(queue):
        curr_path, depth = queue.pop(0)
        if not max_depth or (isinstance(max_depth, int) and depth+1 <= max_depth):
            sub = [(x, depth+1) for x in curr_path.iterdir() if x.is_dir()]
            queue += sub

        if skip_to is not None and skip_to != curr_path.name:
            logging.info("Skipping %s", curr_path.name)
            continue
        skip_to = None
        logging.info("Running on %s", curr_path.name)
        logging.info("--------------------")
        if func(curr_path.relative_to(initial_path)):
            sleep(sleep_time)

def push_sync(device_id, target, lib, current, depth=1) -> bool:
    """
    Run an adb push command to sync libdir with the target
    `target` : base path on device
    `lib`    : base path on source
    `current`: current pos relative to `lib`
    """
    if skip_depth_under(lib, current, depth):
        logging.info("Skipping %s", current)
        return False

    logging.info("Pushing: %s\nto: %s\nBase: %s", lib, target, current)
    logging.info("--------------------")
    result = subprocess.run(["adb",
                             "-t",
                             device_id,
                             "push",
                             "--sync",
                             str(lib / current),
                             str((target / current).parent)],
                            capture_output=True)
    if result.returncode != 0:
        logging.warning("Push Failure")
        logging.warning(result.stdout.decode())
        raise Exception()
    return True


def pull_sync(device_id, target, lib, current, depth=1) -> bool:
    """
    Run an adb pull command to sync device with library
    """
    if skip_depth_under(lib, current, 0):
        logging.info("Skipping %s", current)
        return False

    logging.info("Pulling: %s\nto:\n %s\ncurrent: %s", target, lib, current)
    logging.info("--------------------")
    # Compare the target and lib using find
    device_files = subprocess.run(["adb",
                                   "-t",
                                   device_id,
                                   "shell",
                                   "find",
                                   str(target/current),
                                   "-type", "f"],
                                  capture_output=True)
    if device_files.returncode != 0:
        logging.warning("Push Failure")
        logging.warning(result.stdout.decode())
        raise Exception()

    device_set = { pl.Path(x).relative_to(target) for x in device_files.stdout.decode().split("\n") if x != "" }


    local_files = subprocess.run(["find",
                                  str(lib/current),
                                  "-type", "f"],
                                  capture_output=True)
    if local_files.returncode != 0:
        logging.warning("Push Failure")
        logging.warning(result.stdout.decode())
        raise Exception()
    local_set = {pl.Path(x).relative_to(lib) for x in local_files.stdout.decode().split("\n") if x != ""}

    missing = device_set - local_set
    logging.info("%s missing from %s", len(missing), lib/current)
    # Then copy missing over
    for path in missing:
        assert(not (lib/path).exists())
        if not (lib/path).parent.exists():
            (lib/path).parent.mkdir()

        logging.info("Copying: %s\nTo: %s", target/path, lib/path)
        result = subprocess.run(["adb",
                                "-t",
                                 device_id,
                                "pull",
                                 str(target/path),
                                 str(lib/path)],
                                capture_output=True)
        assert((lib/path).exists()), lib/path
        if result.returncode != 0:
            logging.warning("Push Failure")
            logging.warning(result.stdout.decode())
            raise Exception()

    return True

def main():
    logging.info("Starting ADB Unifier")
    args        = parser.parse_args()
    args.config = pl.Path(args.config).expanduser().resolve()

    if not (args.to_device or args.from_device):
        logging.info("Option Missing: --to-device or --from-device")
        exit()

    config = ConfigParser(allow_no_value=True, delimiters='=')
    config.read(args.config)
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
                           lib_path,
                           depth=args.depthskip)

    logging.info("DFS for: %s\nto: %s", lib_path, target_path)
    # Run the walk
    try:
        dfs_dir(lib_path,
                args.wait,
                partial_func,
                skip_to=args.skip_to,
                max_depth=args.max_depth)
    except Exception:
        say("DFS Failure")

if __name__ == '__main__':
    main()

##-- adb_shell_example
    # from adb_shell.adb_device import AdbDeviceTcp
    # from adb_shell.auth.sign_pythonrsa import PythonRSASigner
    # from ppadb.client import Client
    # # Load the public and private keys
    # adbkey = expander(config['ADB']['keyloc'])
    # with open(adbkey) as f:
    #     priv = f.read()
    # with open(adbkey + '.pub') as f:
    #     pub = f.read()
    # signer = PythonRSASigner(pub, priv)

    # # Connect
    # try:
    #     shell_device = AdbDeviceTcp(config['ADB']['ipaddr'], 5555, default_transport_timeout_s=9.)
    #     shell_device.connect(rsa_keys=[signer], auth_timeout_s=int(config['ADB']['auth_timeout']))
    # except ConnectionRefusedError as err:
    #     logging.info("Shell Connection Refused")
    #     exit()

    # try:
    #     client = Client()
    #     adb_device = client.device(config['ADB']['ipaddr'] + ":5555")
    # except Exception as err:
    #     logging.info("ppadb Connection Refused")
    #     exit()

    # logging.info("Connected")

    # # Send a shell command
    # response1 = shell_device.shell(f"ls {config['ADB']['sdcard']}")
    # print(response1)

    # # Find all pdf and epubs in the target
    # instruction  = 'find {} -name "*.pdf"'.format(join(config['ADB']['sdcard'], args.target))
    # logging.info("Find Instruction: %s", instruction)
    # all_files = [x for x in shell_device.shell(instruction).split("\n") if x != ""]
    # logging.info("Found %s files in %s", len(all_files), args.target)
    # print(all_files)
##-- End adb_shell_example
