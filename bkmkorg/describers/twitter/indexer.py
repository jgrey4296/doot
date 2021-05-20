#!/opt/anaconda3/envs/bookmark/bin/python
##!/opt/anaconda3/envs/bookmark/bin/python

from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
import re
from collections import defaultdict

from bkmkorg/utils.file.retrieval import get_data_files

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Index all users found in orgs"]))
parser.add_argument('--target', action="append")
parser.add_argument('--output')


PERMALINK = re.compile(r':PERMALINK:\s+\[\[https?://twitter.com/(.+?)/status/[0-9]+\]')
# TODO add @ recognition

if __name__ == '__main__':
    args = parser.parse_args()
    args.target = [abspath(expanduser(x)) for x in args.target]
    args.output = abspath(expanduser(args.output))

    targets = get_data_files(args.target, ext=".org")

    total_index = defaultdict(lambda: set())

    for filename in targets:
        # read in
        lines = []
        with file(filename, 'r') as f:
            lines = f.readlines()

        # PERMALINK
        matched = [PERMALINK.match(x) for x in lines]
        users   = [x[1] for x in matched if bool(x)]
        # add to index
        for user in users:
            total_index[user].add(filename)

    # Write out index
    out_lines = ["@{} :{}".format(x, ":".join(y)) for x,y in total_index.items()]
    out_string = "\n".join(out_lines)
    with open(args.output, 'w') as f:
        f.write(out_string)
