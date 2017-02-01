"""
A Quick file to load and count bookmarks,
to make sure i haven't lost any
"""
from os.path import isfile,join,exists
from os import listdir
import re
from bookmark_organiser.bkmkorg import html_opener 
from bookmark_organiser.bkmkorg import bookmark_simplification as bs
from bookmark_organiser.bkmkorg import netscape_bookmark_exporter as nbe
from bookmark_organiser.bkmkorg import util
from verifySites import verifyUrl
import logging
import IPython
from time import sleep

#Special bookmark files to process first:
FOCUS_FILE = "tor_bookmarks.html"

HTMLREGEX = re.compile(r'.*\.html')
#Extracted data:
ex_data = {}

#setup logging:
LOGLEVEL = logging.DEBUG
logFileName = "tor_tag_consolidation.log"
logging.basicConfig(filename=logFileName,level=LOGLEVEL,filemode='w')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

if not isfile(FOCUS_FILE):
    logging.exception("File does not exist");
    exit()

bookmarks = html_opener.open_and_extract_bookmarks(FOCUS_FILE)

logging.info("Loaded: {}".format(len(bookmarks)))

IPython.embed()


