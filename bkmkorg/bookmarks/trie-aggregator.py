"""
Top level file to combine together all bookmarks
Loads each netscape format html in raw_bookmarks,
extracts each link and name, then organises them,
then exports them to ./cleaned_bookmarks.html,
also in netscape html format
"""
from os.path import isfile,join,exists, expanduser, abspath
from os import listdir
import re
import html_opener
import bookmark_simplification as bs
import netscape_bookmark_exporter as nbe
import plain_exporter as pe
import logging
import IPython
from time import sleep

import argparse

#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser("")
parser.add_argument('-s', '--source', default="~/github/bookmark_organiser/raw_bookmarks")
parser.add_argument('-e', '--export', default="simplified_bookmarks")
parser.add_argument('-v', '--verify', action="store_true")
parser.add_argument('--period', default=20, help="sleep period")
parser.add_argument('--amnt',   default=2, help="sleep amount")

args = parser.parse_args()


#Special bookmark files to process first:
FORCED_ORDER = ["verified_bookmarks.html","partial_tagged_bookmarks.html"]

#Settings
EXPORT_NAME = abspath(expanduser(args.export))
HTMLREGEX = re.compile(r'.*\.html')
VERIFY_TRAILING_SLASH_REMOVAL = re.compile(r'(ftp|http(?:s)?:/(?:/)?)(.*?)(?:/?)$')
RAWDIR = expanduser(args.source)
SLEEP_AMNT = args.amnt
SLEEP_PERIOD = args.period
SPECIFIC_BOOKMARK_FILE = None #"tag_test_bookmarks.html"
VERIFY_FLAG = args.verify

#Extracted data:
ex_data = {}
#for verification:
allurls = set()

#setup logging:
LOGLEVEL = logging.DEBUG
logFileName = "log.bookmark_consolidation"
logging.basicConfig(filename=logFileName,level=LOGLEVEL,filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)


logging.info("Collecting files")

#Get the html files
rawHtmls = [f for f in listdir(RAWDIR) if isfile(join(RAWDIR,f)) and HTMLREGEX.match(f) and (SPECIFIC_BOOKMARK_FILE is None or f == SPECIFIC_BOOKMARK_FILE) and f not in FORCED_ORDER]
#Override with higher priority files:
orderedHtmls = [x for x in FORCED_ORDER if isfile(join(RAWDIR,x))] + rawHtmls

#inspect continuing
#IPython.embed(simple_prompt=True)

for f in orderedHtmls:
    #Get [(name,url)]s
    logging.info("Processing File: {}".format(f))
    bookmarks = html_opener.open_and_extract_bookmarks(join(RAWDIR,f))
    num_bookmarks = len(bookmarks)
    logging.info("Found {} bookmarks to add".format(num_bookmarks))
    for i,bkmkTuple in enumerate(bookmarks):
            logging.debug("inserting {}/{}: {}".format(i,num_bookmarks,bkmkTuple.name))
            result = bs.insert_trie(ex_data,bkmkTuple)
            #Store the bkmk url in the total url set
            if result:
                allurls.add(bkmkTuple.url)


entries,overwrites = bs.returnCounts()
logging.info("Insertions finished: {} entries | {} overwrites".format(entries,overwrites))
#IPython.embed(simple_prompt=True)
logging.info("Grouping Trie")
finalTrie = bs.groupTrie(ex_data)
logging.info("Converting to html string")

#IPython.embed(simple_prompt=True)
nbe.exportBookmarks(finalTrie, "{}.html".format(EXPORT_NAME))
pe.exportBookmarks(finalTrie, join(".", EXPORT_NAME + ".txt"))
