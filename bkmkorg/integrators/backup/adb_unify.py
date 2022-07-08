#!/usr/bin/env python3
from __future__ import annotations

import abc
import argparse
import logging as logmod
import subprocess
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

data_path    = files(DEFAULT_CONIFG)
data_secrets = data_path.joinpath(DEFAULT_SECRETS)

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Walk through a library directory, and either push to,",
                                                     "or pull from, a tablet to sync the directories"]))
parser.add_argument('--config', default=data_secrets)
parser.add_argument('--library', required=True)
parser.add_argument('--target',  required=True)
parser.add_argument('--to-device',   action='store_true')
parser.add_argument('--from-device', action='store_true')
parser.add_argument('--wait', type=int, default=10)


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
##############################


def expander(path):
    return abspath(expanduser(path))


def dfs_dir(initial, sleep_time, func):
    logging.info("Getting Data Files")
    initial = initial if isinstance(initial, list) else [initial]
    queue = [(x, x) for x in initial]
    while bool(queue):
        rel_path, abs_path = queue.pop(0)
        if isdir(abs_path):
            sub = [(join(rel_path, x), join(abs_path,x)) for x in listdir(abs_path)]
            queue += sub
            logging.info("Running on %s", abs_path)
            func(rel_path)
            sleep(sleep_time)

def push_sync(target, lib, current):
    """
    Run an adb push command to sync libdir with the target
    `target` : base path on device
    `lib`    : base path on source
    `current`: current pos relative to `lib`
    """
    logging.info("Pushing: %s : %s : %s", join(target, current), join(lib, current), current)
    result = subprocess.run(["adb",
                             "-s",
                             "192.168.1.22:5555",
                             "push",
                             "--sync",
                             join(lib, current),
                             join(lib, target)],
                            capture_output=True)
    assert(result.returncode == 0), result.stdout.decode()

def pull_sync(target, lib, current):
    """
    Run an adb pull command to sync device with library
    """
    logging.info("Pulling: %s : %s : %s", join(target, current), join(lib, current), current)
    # Compare the target and lib using find
    device_files = subprocess.run(["adb",
                                   "-s",
                                   "192.168.1.22:5555",
                                   "shell",
                                   "find",
                                   join(target, current),
                                   "-type", "f"],
                                  capture_output=True)
    assert(device_files.returncode == 0), device_files.stdout.decode()
    device_set = { x[len(target):] for x in device_files.stdout.decode().split("\n") }


    local_files = subprocess.run(["find",
                                  join(lib, current),
                                  "-type", "f"],
                                  capture_output=True)
    assert(local_files.returncode == 0), local_files.stdout.decode()
    local_set = {x[len(lib):] for x in device_files.stdout.decode().split("\n")}

    missing = device_set - local_set
    logging.info("%s missing from %s", len(missing), join(lib, current))
    # Then copy missing over
    for path in missing:
        if path[0] == "/":
            path = path[1:]
        assert(not exists(join(lib, path)))
        result = subprocess.run(["adb",
                                "-s",
                                "192.168.1.22:5555",
                                "pull",
                                 join(target, path),
                                 join(lib, path)],
                                capture_output=True)
        assert(exists(join(lib, path)))
        assert(result.returncode == 0), result.stdout.decode()



def main():
    logging.info("Starting ADB Unifier")
    args = parser.parse_args()
    if not (args.to_device or args.from_device):
        logging.info("Option Missing: --to-device or --from-device")
        exit()

    config = ConfigParser(allow_no_value=True, delimiters='=')
    config.read(abspath(expanduser(args.config)))

    # Walk the library directory
    if args.to_device:
        func = push_sync
    elif args.from_device:
        func = pull_sync

    partial_func = partial(func,
                           shell_device,
                           adb_device,
                           join(config['ADB']['sdcard'], args.target),
                           args.library)

    dfs_dir(args.library,
            args.wait,
            partial_func)


if __name__ == '__main__':
    main()

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
