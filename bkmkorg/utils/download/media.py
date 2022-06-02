#!/usr/bin/env python3

from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

from os import system
from os.path import exists, join, splitext, split
from os import listdir
import requests
import logging as root_logger

logging = root_logger.getLogger(__name__)

CHECK_AMNT = 150

def download_media(media_dir, media):
    """ Download all media mentioned in json files """
    logging.info("Downloading media {} to: {}".format(len(media), media_dir))
    remaining = [x for x in media if not exists(join(media_dir, split(x)[1]))]

    if len(remaining) > CHECK_AMNT:
        system('say -v Moira -r 50 "Found a Large Group of Files, waiting for confirmation"')
        result = input("Continue? [y/n] ")
        if result != "y":
            logging.warning("Skipping download")
            return


    scaler = int(len(media) / 100) + 1
    for i, x in enumerate(media):
        if i % scaler == 0:
            logging.info("{}/100".format(int(i/scaler)))

        filename = split(x)[1]
        if exists(join(media_dir, filename)):
            continue

        try:
            request = requests.get(x)
            with open(join(media_dir, filename), 'wb') as f:
                f.write(request.content)
        except Exception as e:
            logging.warning("Error Downloading: {}".format(x))
            logging.warning(str(e))
