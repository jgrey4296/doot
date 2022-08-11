#!/usr/bin/env python3
#see https://docs.python.org/3/howto/argparse.html
##-- imports
from __future__ import annotations

import argparse
try:
    from toml import load
except ImportError:
    from tomli import load

##-- end imports

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))

parser.add_argument('--config', default="/Volumes/documents/github/python/bookmark_organiser/pyproject.toml")


def main():
    args = parser.parse_args()

    with open(args.config, 'rb') as f:
        cfg = load(f)

    print("Entry Points in bkmkorg:")
    entry_points = sorted([x for x in cfg['project']['scripts'].keys()])
    for point in entry_points:
        print("    ", point)

if __name__ == '__main__':
    main()
