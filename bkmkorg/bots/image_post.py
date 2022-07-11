#!/opt/anaconda3/envs/bookmark/bin/python
# Setup root_logger:
from os.path import splitext, split
import logging as root_logger
from os.path import join, isfile, exists, abspath, getsize
from os.path import split, isdir, splitext, expanduser
from os import listdir, system
import subprocess
from random import choice
import argparse
import json
import twitter
from configparser import ConfigParser
from bkmkorg.utils.twitter.api_setup import setup_twitter
from bkmkorg.utils.mastodon.api_setup import setup_mastodon
from importlib.resources import files
from bkmkorg import DEFAULT_CONFIG, DEFAULT_BOTS

data_path = files(f"bkmkorg.{DEFAULT_CONFIG}")
data_bots = data_path.joinpath(DEFAULT_BOTS)

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Auto Tweet/Toot a whitelisted image"]))
parser.add_argument('-c', '--config', default=data_bots, help="The Config File to Use")

args     = parser.parse_args()

expander = lambda x: abspath(expanduser(x))

config   = ConfigParser(allow_no_value=True, delimiters='=')
# Read the main config
config.read(expander(args.config))
# Then read in secrets
config.read(data_path.joinpath(config['DEFAULT']['secrets_loc']))

TEMP_LOC            = config['PHOTO']['TEMP_LOC']
dcim_whitelist_path = data_path.joinpath(config['PHOTO']['WHITE_LIST'])
conversion_args     = config['PHOTO']['convert_args'].split(" ")
convert_cmd         = "convert"


expander = lambda x: abspath(expanduser(x))

def compress_file(filepath):
    #logging.info("Attempting compression of: {}".format(filepath))
    ext = splitext(filepath)[1][1:]

    retcode = subprocess.call([convert_cmd, filepath,
                               *conversion_args,
                               TEMP_LOC])

    if retcode == 0 and getsize(TEMP_LOC) < 5000000:
        return TEMP_LOC
    else:
        logging.warning("Failure converting: {}".format(filepath))
        exit(1)


def main():
    twit     = setup_twitter(config)
    mastodon = setup_mastodon(config)

    with open(expander(dcim_whitelist_path), 'r') as f:
        whitelist = [x.strip() for x in f.readlines()]

    if not bool(whitelist):
        logging.warning("Nothing to tweet from whitelist")
        exit(1)

    selected = choice(whitelist).split(":")
    if not bool(selected) or not exists(selected[0]):
        logging.warning("No Choice Exists")
        quit()

    logging.info("Selected: %s", selected)
    name = "cora"
    if "kira" in selected[0].lower():
        name = "kira"

    #logging.info("Attempting: {}".format(selected))
    msg = name
    the_file = expander(selected[0])
    if len(selected) > 1:
        msg = selected[1].strip()

    #logging.info(f"File size: {getsize(the_file)}")
    if getsize(the_file) > 4500000:
        the_file = compress_file(the_file)

    assert(getsize(the_file) < 5000000)
    assert(exists(the_file))
    assert(splitext(the_file)[1].lower() in [".jpg", ".png", ".gif"])
    try:
        twit.PostUpdate(msg, media=the_file)
    except Exception as err:
        logging.warning("Twitter Post Failed: %s", str(err))

    # post to mastodon
    try:
        media_id = mastodon.media_post(the_file)
        media_id = mastodon.media_update(media_id, description=f"My Cat {name}, I love her so.")
        mastodon.status_post("Cat", media_ids=media_id)
    except Exception as err:
        logging.warning("Mastodon Post Failed: %s", str(err))
    #logging.info("Finished")


if __name__ == "__main__":
    main()
