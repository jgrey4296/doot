# Setup root_logger:
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.wow_scraping"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')
console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
import IPython
from os.path import join, isfile, exists, isdir, splitext, expanduser
from os import listdir
import json
import wow_scraper.wow_scraper as ws

#Globals and constants:
target_file_type = ".html"
data_location = "/Users/jgrey/assets/Assets/Datasets/Quests/QuestDownload"
target_location = "data"
#quest_htmls :: [(filename, fullpath)]
quest_htmls = []
parsed_data = []

#Get the files to process:
listed_directories = [join(data_location, x) for x in listdir(data_location)]
quest_directories = [x for x in listed_directories if isdir(x)]


for qDir in quest_directories:
    poss_files = listdir(qDir)
    actual_files = [x for x in poss_files if isfile(join(qDir, x))]
    html_files = [x for x in actual_files if splitext(x)[1] == target_file_type]
    total_paths = [(x,join(qDir,x)) for x in html_files]
    quest_htmls += total_paths

#Process the files:
for filename, full_path in quest_htmls:
    logging.info("--------------------")
    logging.info("Processing: {}".format(filename))
    logging.info("Path: {}".format(full_path))
    if exists(join(target_location, splitext(filename)[0]) + '.json'):
        logging.warning("Json for file already exists: {}".format(filename)) 
        continue
    
    with open(full_path, 'r') as f:
        data = f.read()
    logging.info("Data read: {}".format(len(data)))
    #parsep
    parsedData = ws.parseData(data)

    logging.info("Data parsed")
    #save
    with open(join(target_location, splitext(filename)[0]) + ".json", 'w') as f:
        json.dump(parsedData, f, indent=4, sort_keys=True)
    logging.info("Data Stored")
