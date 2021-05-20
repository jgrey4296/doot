#!/opt/anaconda3/envs/bookmark/bin/python

import re
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

import requests
from bkmkorg/utils.file.retrieval import get_data_files

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Index all tags found in orgs"]))
parser.add_argument('--target', action="append")
parser.add_argument('--output')

SHORT_URL_RE = re.compile()

if __name__ == '__main__':
    args = parser.parse_args()
    args.target = [abspath(expanduser(x)) for x in args.target]
    args.output = abspath(expanduser(args.output))

    targets = get_data_files(args.target, ext=".org")
    all_urls = set()

    for filename in targets:
        # read in
        lines = []
        with file(filename, 'r') as f:
            lines = f.readlines()

        outlines = []
        for line in lines:
            match = SHORT_URL_RE.match(line)
            if not bool(match):
                outlines.append(line)
                continue

            # Expand the url using a request

            all_urls.add()
            outlines.append()

        # Write out the transformed file
        total_str = "\n".join(outlines)
        with open(filename, 'w') as f:
            f.write(total_str)


    with open(args.output, 'w') as f:
        f.write("\n".join(all_urls))
