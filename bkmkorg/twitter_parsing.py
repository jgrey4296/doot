"""
A Module to parse saved twitter threads 
"""
from bs4 import BeautifulSoup
from os import listdir, mkdir
from os.path import join, isfile, exists, isdir, splitext, expanduser, split
from time import sleep
import util
# Setup root_logger:
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.twitter_parsing"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################


class TwitterParser:

    def __init__(self, theFile):
        self.path = expanduser(theFile)
        self.file_path = splitext(self.path)[0] + "_files"
        self.just_file_name = splitext(split(theFile)[1])[0]
        self.soup = None
        self.data = {}

        if not exists(self.path):
            raise Exception("File Does Not Exist")
        self.setup()

    def setup(self):
        """ Load and parse the specified file """
        logging.info("Loading: {}".format(self.just_file_name))
        with open(self.path, "r") as f:
            self.soup = BeautifulSoup(f, 'lxml')

    def process(self):
        """ Extract information from the file  """
        logging.info("Processing")
        container = self.get_container()
        tweet = self.get_tweet(container)
        ancestors = self.get_ancestors(container)
        descendants = self.get_descendants(container)

        tweet_data = self.process_tweet(tweet)
        ancestor_data = util.ThreadData("Ancestors", [self.process_tweet(x) for x in ancestors])
        descendant_data = []

        descendant_data.append(util.ThreadData("Main Thread", [self.process_tweet(x) for x in descendants['self_thread']]))

        for x in descendants['conversation']:
            data = [self.process_tweet(y) for y in x]
            descendant_data.append(util.ThreadData("Conversation", data))

        descendant_data.append(util.ThreadData("Lone Tweets", [self.process_tweet(x) for x in descendants['lone']]))

        return util.TwitterData(tweet_data,
                                ancestor_data,
                                descendant_data,
                                self.file_path)

    def get_container(self):
        return self.soup.find("div", class_="permalink-container")

    def process_tweet(self, tweet):
        username = self.get_tweet_username(tweet)
        permalink = self.get_tweet_permalink(tweet)
        time = self.get_tweet_time(tweet)
        content = self.get_tweet_content(tweet)
        media = self.get_tweet_media(tweet)
        links = self.get_tweet_links(tweet)

        data = util.TweetData(username, content, media, links, permalink, time)
        return data

    def get_tweet(self, container):
        logging.info("Getting Main Tweet")
        return container.find("div", class_="permalink-tweet-container").find("div",
                                                                              class_="tweet")

    def get_tweet_username(self, tweet):
        return tweet.find("span", class_="username").get_text()

    def get_tweet_permalink(self, tweet):
        if 'data-permalink-path' not in tweet.attrs:
            raise Exception("Tweet has no permalink")
        return tweet['data-permalink-path']

    def get_tweet_time(self, tweet):
        time = tweet.find('small', class_='time')
        if time is None:
            raise Exception("Tweet has no time")
        a = time.find('a')
        if 'data-original-title' in a.attrs:
            return a['data-original-title']
        elif 'title' in a.attrs:
            return a['title']
        else:
            raise Exception('Tweet has No time')

    def get_tweet_content(self, tweet):
        return tweet.find("div", class_="js-tweet-text-container").get_text()

    def get_tweet_media(self, tweet):
        media_container = tweet.find('div', class_='AdaptiveMedia-container')
        media = []
        if media_container is not None:
            media = [x['src'] for x in media_container.find_all("img") if 'class' not in x.attrs or 'avatar' not in x.attrs['class']]
        media = [split(x)[1] for x in media]
        return media

    def get_tweet_links(self, tweet):
        timeline_link = tweet.find_all('a', class_="twitter-timeline-link")
        links = []

        for x in timeline_link:
            if 'data-expanded-url' in x.attrs:
                links.append(x['data-expanded-url'])
            else:
                links.append(x['href'])
        return links

    def get_descendants(self, container):
        logging.info("Getting Descendants")
        descendants = container.find('div', id='descendants')
        if descendants is None:
            return {
                'self_thread' : [],
                'conversation' : [],
                'lone' : []
                }
        self_thread = descendants.find_all('li', class_="ThreadedConversation--selfThread")
        conversations = [x for x in descendants.find_all('li', class_="ThreadedConversation") if util.conversation_p(x)]
        lone_tweets = descendants.find_all("li", class_="ThreadedConversation--loneTweet")

        self_thread_tweets = [x.find_all('div', class_='tweet') for x in self_thread]
        conversation_tweets = [x.find_all('div', class_='tweet') for x in conversations]
        lone_tweets = [x.find_all('div', class_='tweet') for x in lone_tweets]

        return {'self_thread': [y for x in self_thread_tweets for y in x],
                'conversation': conversation_tweets,
                'lone': [y for x in lone_tweets for y in x]}

    def get_ancestors(self, container):
        logging.info("Getting Ancestors")
        ancestors = container.find(id="ancestors")
        if ancestors is not None:
            tweets = ancestors.find_all(class_="tweet")
            return tweets
        return []


if __name__ == "__main__":
    import argparse
    import IPython
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', default="./output")
    parser.add_argument('-c', '--count', default=10)
    parser.add_argument('-s', '--source')
    args = parser.parse_args()

    if not isdir(args.output):
        mkdir(args.output)

    if isfile(args.source):
        parser = TwitterParser(args.source)
        output = parser.process()
        output.save(args.output)
    else:
        assert(isdir(args.source))
        targets = [x for x in listdir(args.source) if splitext(x)[1] == ".html"]
        for i, the_target in enumerate(targets):
            try:
                parser = TwitterParser(join(args.source, the_target))
                output = parser.process()
                output.save(args.output)
            except Exception as e:
                logging.warning("AN ERROR OCCURED FOR: {}".format(the_target))
                with open(join(args.output, "errors.txt"), "a") as f:
                    f.write("{}\n".format(the_target))
            if i % args.count == 0:
                sleep(args.count)
