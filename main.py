"""
Top level file to combine together all bookmarks
Loads each netscape format html in raw_bookmarks,
extracts each link and name, then organises them,
then exports them to ./cleaned_bookmarks.html,
also in netscape html format
"""
from os.path import isfile,join,exists
from os import listdir
import re
from bookmark_organiser.bkmkorg import html_opener 
from bookmark_organiser.bkmkorg import bookmark_simplification as bs
from bookmark_organiser.bkmkorg import netscape_bookmark_exporter as nbe
from bookmark_organiser.bkmkorg import util
import logging
import IPython

RAWDIR = "raw_bookmarks"
EXPORT_NAME = "simplified_bookmarks.html"
SPECIFIC_BOOKMARK_FILE = None #"tag_test_bookmarks.html"
HTMLREGEX = re.compile(r'.*\.html')
#Extracted data:
ex_data = {}
#for verification:
allurls = set()

#setup logging:
LOGLEVEL = logging.DEBUG
logFileName = "bookmark_consolidation.log"
logging.basicConfig(filename=logFileName,level=LOGLEVEL,filemode='w')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

logging.info("Collecting files")


#Get the html files
rawHtmls = [f for f in listdir(RAWDIR) if isfile(join(RAWDIR,f)) and HTMLREGEX.match(f) and (SPECIFIC_BOOKMARK_FILE is None or f == SPECIFIC_BOOKMARK_FILE)]

for f in rawHtmls:
    #Get [(name,url)]s
    logging.info("Processing File: {}".format(f))
    bookmarks = html_opener.open_and_extract_bookmarks(join(RAWDIR,f))

    for bkmkTuple in bookmarks:
        logging.debug("inserting: {}".format(bkmkTuple.name))
        result = bs.insert_trie(ex_data,bkmkTuple)
        if result:
            allurls.add(bkmkTuple.url)

entries,overwrites = bs.returnCounts()
logging.info("Insertions finished: {} entries | {} overwrites".format(entries,overwrites))        
#IPython.embed()
logging.info("Grouping Trie")
finalTrie = bs.groupTrie(ex_data)
logging.info("Converting to html string")

IPython.embed()
bookmark_html_string = nbe.exportBookmarks(finalTrie)
verifyTrailingSlashRemoval = re.compile(r'(.*?)(?:/?)$')
#verify:
for url in allurls:
    snippedUrl = verifyTrailingSlashRemoval.findall(url)[0]
    if snippedUrl not in bookmark_html_string:
        #raise Exception("Missing Url: {}".format(snippedUrl))
        logging.warning("Unsnipped Url: {}".format(url))
        logging.warning("Missing Url: {}".format(snippedUrl))
        IPython.embed()

logging.info("Saving html string")
util.writeToFile(join(".",EXPORT_NAME),bookmark_html_string)

        
