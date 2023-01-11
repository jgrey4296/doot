#!/usr/bin/env python3
##-- imports
from os import system
import pathlib as pl
from datetime import datetime
import argparse
from importlib.resources import files
from bkmkorg import DEFAULT_CONFIG, DEFAULT_BOTS

try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml
##-- end imports

##-- data
data_path = files(DEFAULT_CONFIG)
data_bots= data_path / DEFAULT_BOTS
##-- end data

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Trigger Mac OS to speak the time"]))
parser.add_argument('--config', default=data_bots)
args = parser.parse_args()
##-- end argparse

def main():
    config = toml.load(args.config)

    now               = datetime.now()
    now_str           = now.strftime(config['TIME']['format'])
    formatted_command = config['TIME']['cmd'].format(now_str)
    system(formatted_command)


##-- ifmain
if __name__ == "__main__":
    main()

##-- end ifmain
