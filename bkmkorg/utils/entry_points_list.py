#!/usr/bin/env python3
#see https://docs.python.org/3/howto/argparse.html
import argparse
import configparser
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))

parser.add_argument('--config', default="/Volumes/documents/github/py_bookmark_organiser/setup.cfg")


def main():
    args = parser.parse_args()

    cfg = configparser.ConfigParser()
    cfg.read(args.config)

    print("Entry Points in bkmkorg:")
    entry_points = sorted([x.split("=")[0].strip() for x in cfg['options.entry_points']['console_scripts'].split("\n") if bool(x)])
    for point in entry_points:
        print("    ", point)

if __name__ == '__main__':
    main()
