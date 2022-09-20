#!/usr/bin/env python3
##-- imports
from os import system
import pathlib as pl
from configparser import ConfigParser
from datetime import datetime
import argparse
from importlib.resources import files
from bkmkorg import DEFAULT_CONFIG, DEFAULT_BOTS

##-- end imports

##-- data
data_path = files(f"bkmkorg.{DEFAULT_CONFIG}")
data_bots= data_path / DEFAULT_BOTS
##-- end data

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Trigger Mac OS to speak the time"]))
parser.add_argument('--config', default=data_bots)
args = parser.parse_args()
##-- end argparse




def main():
    config = ConfigParser(allow_no_value=True, delimiters='=')
    config.read(pl.Path(args.config).expanduser().resolve())

    now               = datetime.now()
    now_str           = now.strftime(config['TIME']['format'])
    formatted_command = config['TIME']['cmd'].format(now_str)
    system(formatted_command)


if __name__ == "__main__":
    main()
