#!/usr/bin/env python3
import re
import logging as root_logger
logging = root_logger.getLogger(__name__)

def check_orgs(org_files, id_regex=r"^\s+:(PERMALINK|TIME):\s+$"):
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
