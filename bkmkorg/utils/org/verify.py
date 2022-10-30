#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import logging as root_logger
import pathlib as pl
import re
##-- end imports

logging = root_logger.getLogger(__name__)

def check_orgs(org_files:list[pl.Path], id_regex=r"^\s+:(PERMALINK|TIME):\s+$"):
    """
    given paths to org files,
    extract permalinks
    """
    logging.info("Checking Orgs")
    ORG_ID_REGEX = re.compile(id_regex)
    files        = set([])

    for org in org_files:
        #read
        text = []
        with open(org,'r') as f:
            text = f.readlines()

        #line by line
        for line in text:
            match = ORG_ID_REGEX.match(line)
            if not bool(match):
                continue

            files.add(org)
            break

    return files
