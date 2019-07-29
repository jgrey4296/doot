"""
A Simple File to scrape Scenes from a Multiverse by Jon Rosenberg
"""
##############################
# IMPORTS
####################
# Setup root_logger:
import logging as root_logger
import re
import IPython
from urllib import parse, request
from datetime import datetime
from bs4 import BeautifulSoup
from os.path import join, isfile, split
from os.path import exists, isdir, splitext, expanduser
from os import listdir, mkdir
from functools import partial
from time import sleep


#Log Setup
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.sfam"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
# CONSTANTS
####################
STARTING_PAGE = "https://amultiverse.com/archive"
RETRIEVE_COUNT = 10
WAIT_TIME = 5
DATA_LOCATION = "data"
IMAGE_LOCATION = "imgs"
START_YEAR = "2010"
COMIC_TEMPLATE = "comic_{}.html"
COMIC_REGEX = re.compile(u'comic_([\\d_]+)')
ROOT = "root.html"
YEAR_TEMPLATE = "year_{}.html"
YEAR_REGEX = re.compile(u'year_(\\d+)')
DATE_FORMAT = "%Y %b %d"
DATE_OUTPUT = "%Y_%m_%d"
##############################
# VARIABLES
####################
current_count = 0
current_html_data = None
##############################
# Utilities
####################
def is_class_x(x, tag):
    return tag.has_attr('class') and tag.get('class')[0] == x

def is_id_x(x, tag):
    return tag.has_attr('id') and tag.get('id') == x

def check_count():
    global current_count
    if current_count < RETRIEVE_COUNT:
        current_count += 1
        sleep(30)
    else:
        logging.info("Sleeping")
        sleep(60 * WAIT_TIME)
        current_count = 0

def download_and_save(target, filename, base=DATA_LOCATION):
    if exists(join(base, filename)):
        logging.info("Skipping: {}".format(filename))
        return
    check_count()
    try:
        with open(join(base, filename), 'wb') as f:
            with request.urlopen(target) as r:
                f.write(r.read())
    except urllib.error.URLError as e:
        logging.exception(e)
        IPython.embed(simple_prompt=True)

def convert_date(year, month_day):
    return datetime.strptime("{} {}".format(year, month_day), DATE_FORMAT).strftime(DATE_OUTPUT)

##############################
# Core Functions
####################

########################################
if __name__ == "__main__":
    global current_html_data
    logging.info("Starting SFAM Scraper")

    if not exists(DATA_LOCATION):
        #Create the data location
        logging.info("Creating Data Location")
        mkdir(DATA_LOCATION)
    if not exists(IMAGE_LOCATION):
        #create the image location
        logging.info("Creating Image Location")
        mkdir(IMAGE_LOCATION)
    if not exists(join(DATA_LOCATION, ROOT)):
        #Get the root
        logging.info("Saving Root")
        download_and_save(STARTING_PAGE, ROOT)

    #extract the links to archive pages
    with open(join(DATA_LOCATION, ROOT), 'rb') as f:
        current_html_data = BeautifulSoup(f.read(), 'html.parser')

    if current_html_data is None:
        raise Exception("No Current Data")

    #get the archive pages
    logging.info("Retrieving archive years")
    div_archive_links = current_html_data.find(partial(is_class_x, 'archive-yearlist'))
    links = div_archive_links.find_all('a')
    link_texts = [(x.string, x.get('href')) for x in links]

    #get The Individual years
    for (year, link) in link_texts:
        logging.info("Retrieving information for Year: {}".format(year))
        download_and_save(parse.urljoin(STARTING_PAGE, link), YEAR_TEMPLATE.format(year))

    for x in listdir(DATA_LOCATION):
        name, ftype = splitext(x)
        if ftype != '.html' or not bool(YEAR_REGEX.match(name)):
            logging.info("Skipping: {} - {}".format(x,
                                                    bool(YEAR_REGEX.match(name))))
            continue
        #Get the file
        year = YEAR_REGEX.match(name).group(1)
        logging.info("Loading info for year: {}".format(year))

        #extract the links
        with open(join(DATA_LOCATION, x), 'rb') as f:
            current_html_data = BeautifulSoup(f.read(), 'html.parser')

        archive_date = partial(is_class_x, 'archive-date')
        archive_title = partial(is_class_x, 'archive-title')
        month_table = current_html_data.find(partial(is_class_x, 'month-table'))
        trs = month_table.find_all('tr')
        date_links = [(convert_date(year,
                                    x.find(archive_date).string),
                       x.find('a').get('href')) for x in trs]

        for d, l in date_links:
            #if they don't exist, retrieve them, save them
            logging.info("Retrieving information for comic: {}".format(d))
            download_and_save(l, COMIC_TEMPLATE.format(d))


    for x in listdir(DATA_LOCATION):
        name, ftype = splitext(x)
        if ftype != '.html' or not bool(COMIC_REGEX.match(name)):
            logging.info("Skipping: {}".format(name))
            continue
        #find the image name
        logging.info("Loading info for: {}".format(name))
        #check it doesn't already exist
        with open(join(DATA_LOCATION, x), 'rb') as f:
            current_html_data = BeautifulSoup(f.read(), 'html.parser')

        comic = current_html_data.find(partial(is_id_x, 'comic'))
        img = comic.find('img')
        if img is None:
            continue
        link = img.get('src')
        image_name = split(link)[1]
        download_and_save(link, image_name, base=IMAGE_LOCATION)

    IPython.embed(simple_prompt=True)
