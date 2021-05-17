import logging
from collections import namedtuple
from hashlib import sha256
from os import getcwd, mkdir
from os.path import abspath, exists, isdir, isfile, join, split, splitext
from shutil import copyfile

import regex

hashtag_re = regex.compile(r'#(\w+)')
http_re    = regex.compile(r'(http|pic\.twitter)')


def conversation_p(tag):
    """ A Simple twitter conversation predicate """
    cls = tag['class']
    tc = "ThreadedConversation" in cls
    tcs = "ThreadedConversation--selfThread" in cls
    lt = "ThreadedConversation--loneTweet" in cls
    return tc and not (tcs or lt)

class TweetData:
    """ A Simple Class to hold tweet data """

    def __init__(self, username,
                 content,
                 media,
                 links,
                 permalink,
                 time,
                 videos=None,
                 quoted=None):
        self.username = username
        self.content = content
        self.media = media
        if not media:
            self.media = []
        self.links = links
        if not links:
            self.links = []
        self.permalink = permalink
        self.time = time
        self.videos = videos
        if not videos:
            self.videos = []
        if not videos:
            self.videos = []
        self.quoted = quoted


    def to_org(self, media_dir, indent=3):
        tags = []
        if bool(self.links):
            tags.append("has_link")
        if bool(self.media):
            tags.append("has_media")

        permalink = ":PERMALINK: [[https://twitter.com{}][{}]]".format(self.permalink,
                                                                       self.permalink)
        time = ":TIME: {}".format(self.time)

        media = "\n".join(["[[file:{}][{}]]".format(join(media_dir,x),x) for x in self.media])
        links = "\n".join(["[[{}][{}]]".format(x,x) for x in self.links])

        cleaned_content = self.content.replace("\n", "")
        new_lined_content, count = http_re.subn("\n\g<0>", cleaned_content)
        quoted = ""
        if self.quoted:
            quoted = self.quoted.to_org(media_dir, indent=4) + "\n"

        hashtags = hashtag_re.findall(new_lined_content)
        tags += hashtags

        total_content = "{}\n{}{}\n{}".format(new_lined_content, quoted, media, links)

        gap = ""
        tagStr = ""
        if bool(tags):
            gap = " " * 20
            tagStr = ":{}:".format(":".join(set(tags)))

        header = "{} {}{}{}\n".format(indent*"*", self.username,gap,tagStr)
        props = ":PROPERTIES:\n{}\n{}\n:END:\n".format(permalink, time)


        return "{}{}{}\n".format(header,props,total_content)

class ThreadData:
    """ A Simple class to hold twitter threads """

    def __init__(self, name, tweets):
        #threads are lists of lists of tweets
        self.tweets = [x for x in tweets if x is not None]
        self.name = name

    def usernames(self):
        return set([x.username for x in self.tweets])

    def links(self):
        return [y for x in self.tweets for y in x.links]

    def media(self):
        return [y for x in self.tweets for y in x.media]

    def videos(self):
        return [y for x in self.tweets for y in x.videos]

    def __len__(self):
        return len(self.tweets)

    def to_org(self, media_dir, indent=3):
        if len(self) == 0:
            return ""

        subthread = "{} {} ({})".format(indent * "*", self.name, len(self.tweets))
        tweets = "\n".join([x.to_org(media_dir, indent + 1) for x in self.tweets])
        return "{}\n{}".format(subthread,
                               tweets)

class TwitterData:
    """ A Simple Class to hold an entire saved twitter page """

    def __init__(self, tweet, ancestors, descendants, file_path):
        self.tweet = tweet
        self.ancestors = ancestors
        self.descendants = descendants
        self.file_path = file_path

    def base_user_str(self):
        return self.tweet.username[1:]

    def usernames(self):
        usernames = [self.tweet.username]
        usernames += [y for x in self.descendants for y in x.usernames()]
        usernames += self.ancestors.usernames()
        return set(usernames)

    def links(self):
        links = []
        links += self.tweet.links
        links += self.ancestors.links()
        links += [y for x in self.descendants for y in x.links()]
        return set(links)

    def media(self):
        media = []
        media += self.tweet.media
        media += self.ancestors.media()
        media += [y for x in self.descendants for y in x.media()]
        return set(media)

    def videos(self):
        videos = []
        videos += self.tweet.videos
        videos += self.ancestors.videos()
        videos += [y for x in self.descendants for y in x.videos()]
        return set(videos)

    def media_to_org(self, media_dir):
        media = self.media()
        if not bool(media):
            return ""
        result = []
        for x in media:
            the_path = join(media_dir, x)
            result.append("[[file:{}][{}]]\n".format(the_path, x))
        as_org = "{} Media ({})\n{}".format(3 * "*",
                                            len(result),
                                            "\n".join(result))
        return as_org

    def videos_to_org(self, media_dir):
        videos = self.videos()
        if not bool(videos):
            return ""
        result = []
        for x in videos:
            filename = split(x)[1]
            the_path = join("https://video.twimg.com/tweet_video", filename)
            result.append("[[{}][{}]]\n".format(the_path, filename))
        as_org = "{} Videos ({})\n{}".format(3 * "*",
                                             len(result),
                                             "\n".join(result))
        return as_org


    def links_to_org(self):
        links = self.links()
        if not bool(links):
            return ""

        formatted_links = ["[[{}][{}]]".format(x,x) for x in links]
        return "{} Links ({})\n{}".format(3 * "*",
                                          len(links),
                                          "\n".join(formatted_links))

    def to_org(self, media_dir):
        """ Print as an Org Document """
        header = "** Thread: {}\n".format(self.tweet.time)

        #add ancestors if any
        ancestors = self.ancestors.to_org(media_dir, 3)

        #add tweet
        tweet = self.tweet.to_org(media_dir, 3)

        #add descendants if any
        descendants = ""
        if len(self.descendants) > 0:
            desc_strs = "\n".join([x.to_org(media_dir, 4) for x in self.descendants])
            descendants = "*** Descendants ({})\n{}".format(len(self.descendants),
                                                            desc_strs)


        media = self.media_to_org(media_dir)
        videos = self.videos_to_org(media_dir)
        links = self.links_to_org()


        return "{}{}{}{}{}{}{}\n".format(header,
                                         ancestors,
                                         tweet,
                                         descendants,
                                         media,
                                         videos,
                                         links)

    def save(self, directory):
        """ Create a subdirectory, org file, and copy images in,
        while converting paths to local """
        base_user = self.base_user_str()
        base_user_files = join(directory, base_user + "_files")
        base_user_org = abspath(join(directory, base_user + ".org"))
        logging.info("Saving to: {}".format(base_user_org))
        #create directory for base user if it doesn't exist
        if not isdir(abspath(base_user_files)):
            mkdir(abspath(base_user_files))
        #copy media in
        self.move_files(base_user_files)
        self.move_videos(base_user_files)

        if not exists(abspath(base_user_org)):
            with open(abspath(base_user_org), "w") as f:
                f.write("* {}'s Threads\n".format(base_user))

        #append in org data
        with open(abspath(base_user_org), 'a') as f:
            f.write(self.to_org(base_user + "_files"))

    def move_files(self, new_dir):
        media = self.media()
        #join with file_path
        old_paths = [join(self.file_path,x) for x in media]
        #join with new_file_path
        new_paths = [join(new_dir,x) for x in media]

        #move a -> b
        for x,y in zip(old_paths, new_paths):
            if exists(y) and not self.check_hashes(x,y):
                logging.warning("File already exists: {} {}".format(x, y))
            if not exists(x):
                raise Exception("File Doesn't Exist: {}".format(x))
                continue
            copyfile(x, y)

    def move_videos(self, new_dir):
        videos = self.videos()
        #Pair the url with the path to download to:
        new_paths = [(x, join(new_dir,split(x)[1])) for x in videos]

        #download
        for x,y in new_paths:
            if exists(y):
                raise Exception("File already exists: {} {}".format(x, y))
            #TODO: download file
            #copyfile(x, y)

    def check_hashes(self, a, b):
        a_hash = ""
        b_hash = "5"
        with open(abspath(a), 'rb') as f:
            a_hash = sha256(f.read()).hexdigest()
        with open(abspath(b), 'rb') as f:
            b_hash = sha256(f.read()).hexdigest()
        return a_hash == b_hash
