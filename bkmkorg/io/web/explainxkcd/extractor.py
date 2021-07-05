#!/opt/anaconda3/envs/bookmark/bin/python
#
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
from bs4 import BeautifulSoup
import argparse
# Setup root_logger:
from os.path import splitext, split
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join([""]))
parser.add_argument("--target", action="append")
parser.add_argument("--sep", default=" _|_ ")
parser.add_argument("--output")


##############################

forbidden = ["Template:create", "index.php/Talk", "index.php?title=Talk"]

def extract(bs):
    data = []

    table = bs.find('tbody')
    trs = table.find_all('tr')

    for tr in trs:
        links = [x['href'] for x in tr.find_all('a') if not any([y in x['href'] for y in forbidden])]
        date = None
        try:
            date  = tr.find(attrs={'data-sort-type' : 'isoDate'}).text
        except AttributeError:
            pass
        data.append((links, date))

    logging.info(f"Extracted {len(data)}")
    return data

if __name__ == '__main__':
    args = parser.parse_args()
    args.target = [abspath(expanduser(x)) for x in args.target]
    args.output = abspath(expanduser(args.output))

    extracted_data = []

    for x in args.target:
        logging.info(f"Reading: {x}")
        with open(x,'r') as f:
            data = BeautifulSoup(f.read(), features="lxml")

        # Extract data
        extracted_data += extract(data)

    # Convert to string:
    output_strs = []
    for entry in extracted_data:
        output_strs.append("{}{}{}".format(args.sep.join(entry[0]), args.sep, entry[1]))

    # Write out
    logging.info("Writing out")
    with open(args.output, 'w') as f:
        f.write("\n".join(output_strs))
