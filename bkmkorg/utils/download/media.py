#!/usr/bin/env python3
##-- imports
from __future__ import annotations

from os import system
from os.path import split
import logging as root_logger
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import requests
##-- end imports

logging = root_logger.getLogger(__name__)

CHECK_AMNT = 150

def download_media(media_dir:pl.Path, media):
    """ Download all media mentioned in json files """
    logging.info("Downloading media %s to: %s", len(media), media_dir)
    remaining = [x for x in media if not (media_dir / split(x)[1]).exists()]

    if len(remaining) > CHECK_AMNT:
        system('say -v Moira -r 50 "Found a Large Group of Files, waiting for confirmation"')
        result = input("Continue? [y/n] ")
        if result != "y":
            logging.warning("Skipping download")
            return

    scaler = int(len(media) / 100) + 1
    for i, x in enumerate(media):
        if i % scaler == 0:
            logging.info("%s/100", int(i/scaler))

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
