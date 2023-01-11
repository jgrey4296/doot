#!/opt/anaconda3/envs/bookmark/bin/python
##-- imports
from __future__ import annotations

from math import inf
import argparse
import json
import logging as root_logger
import pathlib as pl
import re
import subprocess
from importlib.resources import files
from random import choice
try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml

import twitter
from bkmkorg import DEFAULT_BOTS, DEFAULT_CONFIG
from bkmkorg.files.size import human
from bkmkorg.mastodon.api_setup import setup_mastodon
from bkmkorg.twitter.api_setup import setup_twitter
from mastodon import MastodonAPIError

##-- end imports

##-- resources
data_path = files(DEFAULT_CONFIG)
data_bots = data_path / DEFAULT_BOTS
##-- end resources

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.WARN)
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
config   = toml.load(pl.Path(args.config))
# Then read in secrets
secrets = toml.load(data_path / config['DEFAULT']['secrets_loc'])

TEMP_LOC            = pl.Path(config['PHOTO']['TEMP_LOC'])
dcim_whitelist_path = data_path / config['PHOTO']['WHITE_LIST']
conversion_args     = config['PHOTO']['convert_args']
convert_cmd         = "convert"

RESOLUTION_BLACKLIST = data_path / config['PHOTO']['resolution_blacklist']
RESOLUTION_RE        = re.compile(r".*?([0-9]+x[0-9]+)")
##-- end config

def get_resolution(filepath:Path) -> str:
    result = subprocess.run(["file", str(filepath)], capture_output=True)
    if result.returncode == 0:
        res = RESOLUTION_RE.match(result.stdout.decode())
        return res[1]

    raise Exception("Couldn't get image resolution", filepath, result.stdout.decode(), result.stderr.decode())


def compress_file(filepath:Path):
    #logging.info("Attempting compression of: %s", filepath)
    assert(isinstance(filepath, pl.Path) and filepath.exists())
    ext = filepath.suffix

    result = subprocess.run([convert_cmd, str(filepath),
                               *conversion_args,
                               str(TEMP_LOC)],
                             capture_output=True)

    if result.returncode == 0 and TEMP_LOC.stat().st_size < 5000000:
        return TEMP_LOC
    else:
        stdout = result.stdout.decode()
        stderr = result.stderr.decode()
        raise Exception("Failed to convert: {} : {} : {}".format(filepath, stdout, stderr))



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
        logging.warning("Twitter Post Failed: %s", err)

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
            logging.info("Image is too big %s: %s", selected_file, res)
            return

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
    twit     = setup_twitter(secrets)
    mastodon = setup_mastodon(secrets)

    with open(dcim_whitelist_path, 'r') as f:
        whitelist = [x.strip() for x in f.readlines()]

    if not bool(whitelist):
        logging.warning("Nothing to tweet from whitelist")
        exit(1)

    selection     = choice(whitelist).split(":")
    selected_file : str = selection[0]
    msg           = selection[1] if len(selection) > 1 else ""

    selected_file : Path = pl.Path(selected_file)
    selected_file = selected_file.expanduser().resolve()
    if not selected_file.exists():
        logging.warning("Selected File Doesn't Exist: %s", selected_file)
        quit()

    logging.info("Selected: %s", selected_file)
    if not bool(msg):
        msg = "cora"
        if "kira" in selected_file.parent.name.lower():
            msg = "kira"

    logging.info("File size: %s", human(selected_file.stat().st_size))
    post_to_twitter(selected_file, msg, twit)
    post_to_mastodon(selected_file, msg, mastodon)
    logging.info("Finished")


##-- ifmain
if __name__ == "__main__":
    main()

##-- end ifmain
