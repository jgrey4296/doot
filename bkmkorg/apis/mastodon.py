##!/usr/bin/env python3
# pylint: disable=no-member
##-- imports
from __future__ import annotations

import re
import pathlib as pl
import logging as logmod
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast, Final)

import mastodon
##-- end imports

import doot
from doot import TomlAccess

logging = logmod.getLogger(__name__)

toot_size            : Final = doot.config.on_fail(250, int).tool.doot.mastodon.toot_size()
toot_image_size      : Final = doot.config.on_fail("8mb", str).tool.doot.mastodon.image_size()
RESOLUTION_BLACKLIST : Final = doot.locs.image_blacklist

RESOLUTION_RE        : Final = re.compile(r".*?([0-9]+x[0-9]+)")

class MastodonMixin:

    mastodon : mastodon.Mastodon
    resolution_blacklist : set() = set()

    def setup_mastodon(self, config:pl.Path|str):
        logging.info("---------- Initialising Mastodon")
        secrets = TomlAccess.load(pl.Path(config).expanduser())
        instance = mastodon.Mastodon(
            access_token = secrets.mastodon.access_token,
            api_base_url = secrets.mastodon.url
        )

        self.mastodon = instance

    def post_toot(self, task):
        try:
            print("Posting Toot")
            msg = task.values['msg']
            if len(msg) >= toot_size:
                logging.warning("Resulting Tweet too long for mastodon: %s\n%s", len(tweet_text), tweet_text)
            else:
                result = self.mastodon.status_post(msg)
                return { "toot_result": True }
        except Exception as err:
            logging.warning("Mastodon Post Failure: %s", err)
            return { "toot_result": False }

    def post_mastodon_image(self, task):
        try:
            print("Posting Toot Image")
            # 8MB
            msg  = task.values.get('msg', "")
            desc = task.values.get('desc', "")
            the_file    = pl.Path(task.values['image']).expanduser()
            # if the_file.stat().st_size > 8_000_000:
                # the_file = compress_file(the_file)

            assert(the_file.exists())
            assert(the_file.stat().st_size < 8_000_000)
            assert(the_file.suffix.lower() in [".jpg", ".png", ".gif"])

            media_id = self.mastodon.media_post(str(the_file), description=desc)
            # media_id = self.mastodon.media_update(media_id, description=desc)
            self.mastodon.status_post(msg, media_ids=media_id)
            print("Image Toot Posted")
            return { "toot_result": True }
        except mastodon.MastodonAPIError as err:
            general, errcode, form, detail = err.args
            resolution = RESOLUTION_RE.match(detail)
            if resolution and resolution in self.resolution_blacklist:
                pass
            elif errcode == 422 and form == "Unprocessable Entity" and resolution:
                with open(RESOLUTION_BLACKLIST, 'a') as f:
                    f.write("\n" + resolution[1])

            logging.warning("Mastodon Resolution Failure: %s", str(err))
            return { "toot_result": False }
        except Exception as err:
            logging.warning("Mastodon Post Failed: %s", str(err))
            return { "toot_result": False }

    def handle_resolution(self, task):
        # post to mastodon
        with open(RESOLUTION_BLACKLIST, 'r') as f:
            resolution_blacklist = {x.strip() for x in f.readlines()}

        min_x, min_y = inf, inf

        if bool(resolution_blacklist):
            min_x        = min(int(res.split("x")[0]) for res in resolution_blacklist)
            min_y        = min(int(res.split("x")[1]) for res in resolution_blacklist)

        res : str    = get_resolution(selected_file)
        res_x, res_y = res.split("x")
        res_x, res_y = int(res_x), int(res_y)
        if res in resolution_blacklist or (min_x <= res_x and min_y <= res_y):
            logging.info("Image is too big %s: %s", selected_file, res)
            return


    def get_resolution(self, filepath:Path) -> str:
        result = subprocess.run(["file", str(filepath)], capture_output=True, shell=False)
        if result.returncode == 0:
            res = RESOLUTION_RE.match(result.stdout.decode())
            return res[1]

        raise Exception("Couldn't get image resolution", filepath, result.stdout.decode(), result.stderr.decode())


    def maybe_compress_file(self, task):
        image = task.values['image']
        print("Attempting compression of: %s", image)
        assert(isinstance(filepath, pl.Path) and filepath.exists())
        ext               = filepath.suffix
        conversion_target = self.locs.image_temp.with_suffix(ext)
        convert_cmd = self.cmd(["convert", str(filepath),
                                *conversion_args,
                                str(conversion_target)])
        convert_cmd.execute()

        if self.locs.image_temp.stat().st_size < 5000000:
            return { 'image': self.locs.image_temp }

        return False
