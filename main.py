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
HTMLREGEX = re.compile(r'.*\.html')
#Extracted data:
ex_data = {}

#setup logging:
LOGLEVEL = logging.DEBUG
logFileName = "bookmark_consolidation.log"
logging.basicConfig(filename=logFileName,level=LOGLEVEL,filemode='w')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

logging.info("Collecting files")
#Get the html files
rawHtmls = [f for f in listdir(RAWDIR) if isfile(join(RAWDIR,f)) and HTMLREGEX.match(f)]

for f in rawHtmls:
    #Get [(name,link)]s
    logging.info("Processing File: {}".format(f))
    bookmarks = html_opener.open_and_extract_bookmarks(join(RAWDIR,f))
    for pair in bookmarks:
        logging.debug("inserting: {}".format(pair[0]))
        bs.insert_trie(ex_data,pair)

entries,overwrites = bs.returnCounts()
logging.info("Insertions finished: {} entries | {} overwrites".format(entries,overwrites))        
#IPython.embed()
logging.info("Grouping Trie")
finalTrie = bs.groupTrie(ex_data)
logging.info("Converting to html string")

bookmark_html_string = nbe.exportBookmarks(finalTrie)
logging.info("Saving html string")
util.writeToFile(join(".",EXPORT_NAME),bookmark_html_string)

        
