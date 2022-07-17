#!/usr/bin/env python3
from __future__ import annotations

import abc
import argparse
import logging as logmod
import subprocess
import pathlib
from configparser import ConfigParser
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from functools import partial
from importlib.resources import files
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
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

##-- argparse
data_path    = files(f"bkmkorg.{DEFAULT_CONFIG}")
data_secrets = data_path.joinpath(DEFAULT_SECRETS)

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
##-- End argparse
##-- Logging
DISPLAY_LEVEL = logmod.INFO
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
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


# TODO use asyncio for subprocess control
def expander(path):
    return abspath(expanduser(path))


def skip_depth_under(path, curr, depth=1):
    up_by_depth = path/curr
    for x in range(depth):
        up_by_depth = up_by_depth.parent

    return up_by_depth < path

def dfs_dir(initial_path, sleep_time, func):
    logging.info("Getting Data Files for: %s", initial_path)
    logging.info("--------------------")
    initial = initial_path if isinstance(initial_path, list) else [initial_path]
    queue = [x for x in initial]
    while bool(queue):
        curr_path = queue.pop(0)
        sub = [x for x in curr_path.iterdir() if x.is_dir()]
        queue += sub
        logging.info("Running on %s", curr_path.relative_to(initial_path))
        logging.info("--------------------")
        func(curr_path.relative_to(initial_path))
        sleep(sleep_time)

def push_sync(device_id, target, lib, current, depth=1):
    """
    Run an adb push command to sync libdir with the target
    `target` : base path on device
    `lib`    : base path on source
    `current`: current pos relative to `lib`
    """
    if skip_depth_under(lib, current, depth):
        logging.info("Skipping %s", current)
        return

    logging.info("Pushing: %s\nto: %s\nBase: %s", lib, target, current)
    logging.info("--------------------")
    result = subprocess.run(["adb",
                             "-t",
                             device_id,
                             "push",
                             "--sync",
                             lib/current,
                             (target/current).parent],
                            capture_output=True)
    assert(result.returncode == 0), result.stdout.decode()

def pull_sync(device_id, target, lib, current, depth=1):
    """
    Run an adb pull command to sync device with library
    """
    if skip_depth_under(lib, current, 0):
        logging.info("Skipping %s", current)
        return
    logging.info("Pulling: %s\nto:\n %s\ncurrent: %s", target, lib, current)
    logging.info("--------------------")
    # Compare the target and lib using find
    device_files = subprocess.run(["adb",
                                   "-t",
                                   device_id,
                                   "shell",
                                   "find",
                                   target/current,
                                   "-type", "f"],
                                  capture_output=True)
    assert(device_files.returncode == 0), device_files.stderr.decode()
    device_set = { pathlib.Path(x).relative_to(target) for x in device_files.stdout.decode().split("\n") if x != "" }


    local_files = subprocess.run(["find",
                                  lib/current,
                                  "-type", "f"],
                                  capture_output=True)
    assert(local_files.returncode == 0), local_files.stderr.decode()
    local_set = {pathlib.Path(x).relative_to(lib) for x in local_files.stdout.decode().split("\n") if x != ""}

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
                                 target/path,
                                 (lib/path)],
                                capture_output=True)
        assert((lib/path).exists()), lib/path
        assert(result.returncode == 0), result.stderr.decode()



def main():
    logging.info("Starting ADB Unifier")
    args = parser.parse_args()
    if not (args.to_device or args.from_device):
        logging.info("Option Missing: --to-device or --from-device")
        exit()

    config = ConfigParser(allow_no_value=True, delimiters='=')
    config.read(abspath(expanduser(args.config)))

    # device_id = "{}:{}".format(config['ADB']['ipaddr'], config['ADB']['PORT'])
    device_id = args.id
    # Walk the library directory
    if args.to_device:
        func = push_sync
    elif args.from_device:
        func = pull_sync
    else:
        raise Exception()

    lib_path    = pathlib.Path(args.library).resolve()
    target_path = pathlib.Path(config['ADB']['sdcard'], args.target)

    # Curry the args which won't change
    partial_func = partial(func,
                           device_id,
                           target_path,
                           lib_path,
                           depth=args.depthskip)

    logging.info("DFS for: %s\nto: %s", lib_path, target_path)
    # Run the walk
    dfs_dir(lib_path,
            args.wait,
            partial_func)


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

    logging.info("Connected")

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
