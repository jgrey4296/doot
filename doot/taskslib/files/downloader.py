#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from os import system
from os.path import split
from typing import (Any, Callable, ClassVar, Dict, Final, Generic, Iterable,
                    Iterator, List, Mapping, Match, MutableMapping, Optional,
                    Sequence, Set, Tuple, TypeVar, Union, cast)

import doot
import requests
from doot import tasker

##-- end imports

logging = logmod.getLogger(__name__)

CHECK_AMNT    : Final = doot.config.on_fail(150, int).tool.doot.downloader.check_amnt()
speak_confirm : Final = tasker.ActionsMixin.say(None, "Found a Large Group of Files, waiting for confirmation")

class DownloaderMixin:

    def download_media(self, media_dir:pl.Path, media:list):
        """ Download all media mentioned in json files """
        print("Downloading media %s to: %s" % (len(media), media_dir))
        if not media_dir.exists():
            media_dir.mkdir()
        assert(media_dir.is_dir())

        remaining = [x for x in media if x is not None and not (media_dir / pl.Path(x).name).exists()]

        if len(remaining) > CHECK_AMNT:
            speak_confirm.execute()
            result = input("Continue? [y/n] ")
            if result != "y":
                print("Skipping download")
                return

        scaler = int(len(media) / 100) + 1
        for i, x in enumerate(media):
            if i % scaler == 0:
                print("%s/100" % int(i/scaler))

            filename = media_dir / split(x)[1]
            if filename.exists():
                continue

            try:
                request = requests.get(x)
                with open(filename, 'wb') as f:
                    f.write(request.content)
            except Exception as e:
                logging.warning("Error Downloading: %s", x)
                logging.warning(str(e))
