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
from verifySites import verifyUrl
import logging
import IPython
from time import sleep

#Special bookmark files to process first:
FORCED_ORDER = ["verified_bookmarks.html","partial_tagged_bookmarks.html"]

#Settings
RAWDIR = "raw_bookmarks"
EXPORT_NAME = "simplified_bookmarks.html"
SPECIFIC_BOOKMARK_FILE = None #"tag_test_bookmarks.html"
HTMLREGEX = re.compile(r'.*\.html')
VERIFY_FLAG = True
SLEEP_PERIOD = 20
SLEEP_AMNT = 2
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
rawHtmls = [f for f in listdir(RAWDIR) if isfile(join(RAWDIR,f)) and HTMLREGEX.match(f) and (SPECIFIC_BOOKMARK_FILE is None or f == SPECIFIC_BOOKMARK_FILE) and f not in FORCED_ORDER]

orderedHtmls = [x for x in FORCED_ORDER if isfile(join(RAWDIR,x))] + rawHtmls

IPython.embed()


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

        
