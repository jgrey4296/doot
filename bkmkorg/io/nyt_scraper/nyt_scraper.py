"""
    A NYTimes Archive Scraper
"""
# Setup root_logger:
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "scraper_nytimes.log"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
# IMPORTS
####################
import IPython
import requests
from time import sleep
from os.path import isfile, exists, join
import json

##############################
# CONSTANTS
####################
api_key = None
url = lambda d: "https://api.nytimes.com/svc/archive/v1/{}/{}.json".format(d['year'],d['month'])
api_key_params = lambda k: {'api-key': k }
header = { 'user-agent': 'jg-nyt-nlp-scraper/0.0.1' }
WAIT_TIME = 1
MAX_REQUESTS = 2000
DATE_LOG = 'requested_dates.log'
DATA_DIR = "data"
TIMEOUT= 6.2
LOCAL_COUNT_WAIT = 5

##############################
# VARIABLES
####################
requested_dates = []
total_requests_performed_in_session = 0
requests_remaining = 2000

##############################
# Utilities
####################

def retrieve_api_key():
    """ Get the api key from file, rather than hard code it """
    global api_key
    logging.info('Retrieving API KEY')
    with open('./key', 'r') as f:
        api_key = f.read().strip()
    if api_key is None:
        raise Exception('API_KEY not set')
    logging.info('Key retrieved')

def create_session(params={}, headers={}):
    """ For use as the ctor of a 'with' context """
    logging.info('Creating Session with: {}  --- {}'.format(params,headers))
    session = requests.Session()
    session.params.update(params)
    session.headers.update(headers)
    return session


def prep_request(session, url, params={}, headers={}, data={}):
    """ Packs information together to send a single request for information  """
    logging.info('Prepping Request for: {}'.format(url))
    req = requests.Request('GET', url, params=params, headers=headers, data=data)
    prepped = session.prepare_request(req)
    print('Prepared Request: {}'.format(prepped))
    return prepped


def perform_request_then_wait(session, request):
    """ Request information, get the data or deal with the failure  """
    global total_requests_performed_in_session
    logging.info('Performing Request')
    if total_requests_performed_in_session > MAX_REQUESTS:
        raise Exception('Limit fulfilled')
    total_requests_performed_in_session += 1
    response = session.send(request, timeout=TIMEOUT)
    logging.info('Sleeping')
    sleep(WAIT_TIME)
    if response.status_code >= 400:
        logging.warning('Bad Response Code: {}'.format(response.status_code))
        IPython.embed(simple_prompt=True)
        exit()
    elif 200 <= response.status_code < 300:
        logging.info('Response Received')
    return response


def check_response_header(response):
    """ Check for X-RateLimit fields """
    logging.info('Checking Response Header: Remaining: {}'.format(response.headers['X-RateLimit-Remaining-day']))
    if int(response.headers['X-RateLimit-Remaining-day']) < 1:
        raise Exception('No More Requests Remaining Today')

#--------------------
# Date Utilities
#--------------------
def load_last_date():
    """ Get the last date requested from the record of all retrieved data  """
    global requested_dates
    if len(requested_dates) == 0 and exists(DATE_LOG):
        logging.info('Loading Date Log')
        with open(DATE_LOG, 'r') as f:
            requested_dates = json.load(f)
    else:
        logging.info('Initialising Date Log')
        requested_dates.append({'year': 1851, 'month': 1})
    return requested_dates[-1]

def save_dates():
    """ Save the requested dates to the log  """
    with open(DATE_LOG, 'w') as f:
        json.dump(requested_dates, f)
        logging.info('Date Log Saved')

def increment_date(date):
    """ Increments a date appropriately, giving correct months and folding over to the correct year  """
    global requested_dates
    logging.info('Incrementing Date: {}'.format(date))
    if date != requested_dates[-1]:
        requested_dates.append(date)
    month = date['month'] + 1
    year = date['year']
    if month % 13 == 0:
        month = 1
        year += 1
    new_date ={ 'month': month, 'year': year}
    logging.info("New Date: {}".format(new_date))
    return new_date


#Storing responses
def save_response(response, date):
    """ Create the appropriately dated nyt response json file """
    filename = "nyt_response_{}_{}.json".format(date['year'], date['month'])
    filepath = join(DATA_DIR, filename)
    if exists(filepath):
        raise Exception('File already exists: {}'.format(filepath))
    with open(filepath, 'w') as f:
        f.write(response.text)
    logging.info('Wrote: {}'.format(filename))

##############################
# Core Functions
####################
def main_scrape():
    """ A Main function that retrieves nyt data appropriately """
    local_count = 0
    date = increment_date(load_last_date())
    try:
        with create_session(params=api_key_params(api_key), headers=header) as session:
            while total_requests_performed_in_session < MAX_REQUESTS:
                logging.info("\n--------------------\n          NEW REQUEST\n--------------------")
                req = prep_request(session, url(date))
                response = perform_request_then_wait(session, req)
                save_response(response, date)
                date = increment_date(date)
                check_response_header(response)
                local_count += 1
                if local_count % LOCAL_COUNT_WAIT == 0:
                    logging.info('10 Requests performed, waiting')
                    sleep(10)
    except Exception as e:
        logging.critical(e)
        IPython.embed(simple_prompt=True)
        exit()
    finally:
        save_dates()



########################################
if __name__ == "__main__":
    logging.info("Starting ")
    retrieve_api_key()
    main_scrape()
