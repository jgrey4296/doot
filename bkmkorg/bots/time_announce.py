#!/usr/bin/env python3
from os import system
from os.path import abspath, expanduser
from configparser import ConfigParser
from datetime import datetime
import argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Trigger Mac OS to speak the time"]))
parser.add_argument('--config', default="/Volumes/documents/github/py_bookmark_organiser/bots.config")
args = parser.parse_args()



def main():
    config = ConfigParser(allow_no_value=True, delimiters='=')
    config.read(abspath(expanduser(args.config)))

    now               = datetime.now()
    now_str           = now.strftime(config['TIME']['format'])
    formatted_command = config['TIME']['cmd'].format(now_str)
    system(formatted_command)


if __name__ == "__main__":
    main()
