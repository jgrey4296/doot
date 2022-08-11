#!/opt/anaconda3/envs/bookmark/bin/python
##-- imports
from __future__ import annotations

from math import inf
import argparse
import json
import logging as root_logger
import pathlib
import re
import subprocess
from configparser import ConfigParser
from importlib.resources import files
from os.path import split, splitext
from random import choice

import twitter
from bkmkorg import DEFAULT_BOTS, DEFAULT_CONFIG
from bkmkorg.utils.file.size import human
from bkmkorg.utils.mastodon.api_setup import setup_mastodon
from bkmkorg.utils.twitter.api_setup import setup_twitter
from mastodon import MastodonAPIError

##-- end imports

##-- resources
data_path = files(f"bkmkorg.{DEFAULT_CONFIG}")
data_bots = data_path.joinpath(DEFAULT_BOTS)
##-- end resources

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pathlib.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Auto Tweet/Toot a whitelisted image"]))
parser.add_argument('-c', '--config', default=data_bots, help="The Config File to Use")
args     = parser.parse_args()
##-- end argparse

##-- config
config   = ConfigParser(allow_no_value=True, delimiters='=')
# Read the main config
config.read(pathlib.Path(args.config))
# Then read in secrets
config.read(data_path.joinpath(config['DEFAULT']['secrets_loc']))

TEMP_LOC            = pathlib.Path(config['PHOTO']['TEMP_LOC'])
dcim_whitelist_path = data_path.joinpath(config['PHOTO']['WHITE_LIST'])
conversion_args     = config['PHOTO']['convert_args'].split(" ")
convert_cmd         = "convert"

RESOLUTION_BLACKLIST = data_path.joinpath(config['PHOTO']['resolution_blacklist'])
RESOLUTION_RE        = re.compile(r".*?([0-9]+x[0-9]+)")
##-- end config

def get_resolution(filepath:Path) -> str:
    retcode = subprocess.run(["file", str(filepath)], capture_output=True)
    result = RESOLUTION_RE.match(retcode.stdout.decode())
    if result:
        return result[1]

    raise Exception("Couldn't get image resolution", retcode, filepath, result.stdout, result.stderr)


def compress_file(filepath:Path):
    #logging.info("Attempting compression of: {}".format(filepath))
    assert(isinstance(filepath, pathlib.Path) and filepath.exists())
    ext = filepath.suffix

    retcode = subprocess.run([convert_cmd, str(filepath),
                               *conversion_args,
                               str(TEMP_LOC)])

    if retcode == 0 and TEMP_LOC.stat().st_size < 5000000:
        return TEMP_LOC
    else:
        raise Exception("Failed to convert: {}".format(filepath))



def post_to_twitter(selected_file, msg, twit):
    try:
        the_file = selected_file
        if the_file.stat().st_size > 4_500_000:
            the_file = compress_file(the_file)

        assert(the_file.exists())
        assert(the_file.stat().st_size < 5_000_000)
        assert(the_file.suffix.lower() in [".jpg", ".png", ".gif"])
        twit.PostUpdate(msg, media=str(the_file))
    except Exception as err:
        logging.warning("Twitter Post Failed: %s", str(err))

def post_to_mastodon(selected_file, msg, mastodon):
    # post to mastodon
    try:
        with open(RESOLUTION_BLACKLIST, 'r') as f:
            res_blacklist = {x.strip() for x in f.readlines()}

        min_x, min_y = inf, inf

        if bool(res_blacklist):
            min_x        = min(int(res.split("x")[0]) for res in res_blacklist)
            min_y        = min(int(res.split("x")[1]) for res in res_blacklist)

        res : str    = get_resolution(selected_file)
        res_x, res_y = res.split("x")
        res_x, res_y = int(res_x), int(res_y)
        if res in res_blacklist or (min_x <= res_x and min_y <= res_y):
            raise Exception("Image is too big", selected_file, res)

        # 8MB
        the_file = selected_file
        if the_file.stat().st_size > 8_000_000:
            the_file = compress_file(the_file)


        assert(the_file.exists())
        assert(the_file.stat().st_size < 8_000_000)
        assert(the_file.suffix.lower() in [".jpg", ".png", ".gif"])


        media_id = mastodon.media_post(str(the_file))
        media_id = mastodon.media_update(media_id, description=f"My Cat {msg}")
        mastodon.status_post("Cat", media_ids=media_id)
    except MastodonAPIError as err:
        general, errcode, form, detail = err.args
        resolution = RESOLUTION_RE.match(detail)
        if resolution and resolution in res_blacklist:
            pass
        elif errcode == 422 and form == "Unprocessable Entity" and resolution:
            with open(RESOLUTION_BLACKLIST, 'a') as f:
                f.write(resolution[1])
                f.write("\n")

        logging.warning("Mastodon Resolution Failure: %s", str(err))
    except Exception as err:
        logging.warning("Mastodon Post Failed: %s", str(err))

def main():
    twit     = setup_twitter(config)
    mastodon = setup_mastodon(config)

    with open(dcim_whitelist_path, 'r') as f:
        whitelist = [x.strip() for x in f.readlines()]

    if not bool(whitelist):
        logging.warning("Nothing to tweet from whitelist")
        exit(1)

    selection     = choice(whitelist).split(":")
    selected_file : str = selection[0]
    msg           = selection[1] if len(selection) > 1 else ""

    selected_file : Path = pathlib.Path(selected_file)
    selected_file = selected_file.expanduser().absolute()
    if not selected_file.exists():
        logging.warning("No Choice Exists")
        quit()

    logging.info("Selected: %s", selected_file)
    if not bool(msg):
        msg = "cora"
        if "kira" in selected_file.parent.name.lower():
            msg = "kira"

    logging.info(f"File size: {human(selected_file.stat().st_size)}")
    post_to_twitter(selected_file, msg, twit)
    post_to_mastodon(selected_file, msg, mastodon)
    logging.info("Finished")


if __name__ == "__main__":
    main()
