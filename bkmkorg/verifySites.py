"""
Top level website verification for bookmarks.
Anything that responds with a 400 code gets a 'tocheck'
tag added to its bookmark
"""

from os.path import isfile,join,exists
from os import listdir
import re
import html_opener
import bookmark_simplification as bs
import netscape_bookmark_exporter as nbe
import util
import logging
import IPython
import requests
from time import sleep

TOFIX_TAG = "__tofix"
VERIFIED_TAG = "__verified"

def verifyUrl(url):
    try:
        req = requests.head(url)
        return req.status_code < 400
    except Exception as e:
        return False
