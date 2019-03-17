import IPython
from os.path import isfile, join, isdir, splitext, exists, abspath
from os import mkdir, getcwd
from shutil import copyfile
from hashlib import sha256
import logging
from collections import namedtuple

bookmarkTuple = namedtuple("bookmark","name url tags")

class TweetData:

    def __init__(self, username, content, media, links, permalink, time):
        self.username = username
        self.content = content
        self.media = media
        self.links = links
        self.permalink = permalink
        self.time = time


    def to_org(self, media_dir, header_level="*****"):
        tags = []
        if bool(self.links):
            tags.append("has_link")
        if bool(self.media):
            tags.append(":has_media:")

        permalink = ":PERMALINK: [[https://twitter.com{}][{}]]".format(self.permalink,
                                                                       self.permalink)
        time = ":TIME: {}".format(self.time)

        gap = ""
        tagStr = ""
        if bool(tags):
            gap = "                    "
            tagStr = ":{}:".format(":".join(tags))

        header = "{} {}{}{}\n".format(header_level, self.username,gap,tagStr)
        props = ":PROPERTIES:\n{}\n{}\n:END:\n".format(permalink, time)

        media = "\n".join(["[[file:{}][{}]]".format(join(media_dir,x),x) for x in self.media])
        links = "\n".join(["[[{}][{}]]".format(x,x) for x in self.links])
        content = "{}\n{}\n{}".format(self.content, media, links)

        return "{}{}{}\n".format(header,props,content)

class ThreadData:

    def __init__(self, name, tweets):
        #threads are lists of lists of tweets
        self.tweets = tweets
        self.name = name

    def usernames(self):
        return set([x.username for x in self.tweets])

    def links(self):
        return [y for x in self.tweets for y in x.links]

    def media(self):
        return [y for x in self.tweets for y in x.media]

    def __len__(self):
        return len(self.tweets)

    def to_org(self, media_dir):
        subthread = "**** {}".format(self.name)
        tweets = "\n".join([x.to_org(media_dir) for x in self.tweets])
        return "{}\n{}".format(subthread,
                               tweets)

class TwitterData:

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
        return usernames

    def links(self):
        links = []
        links += self.tweet.links
        links += self.ancestors.links()
        links += [y for x in self.descendants for y in x.links()]
        return links

    def media(self):
        media = []
        media += self.tweet.media
        media += self.ancestors.media()
        media += [y for x in self.descendants for y in x.media()]
        return media

    def media_to_org(self, media_dir):
        media = self.media()
        result = ""
        for x in media:
            the_path = join(media_dir, x)
            result += "[[file:{}][{}]]\n".format(the_path, x)
        return result

    def to_org(self, media_dir):
        """ Print as an Org Document """
        participants = ":{}:".format(":".join(self.usernames()))
        header = "** Thread: {}                    {}\n".format(self.tweet.time,
                                                                participants)
        #add ancestors if any
        ancestors = ""
        if len(self.ancestors) > 0:
            ancestors = "*** Ancestors\n{}".format(self.ancestors.to_org(media_dir))

        #add tweet
        tweet = self.tweet.to_org(media_dir, header_level="***")

        #add descendants if any
        descendants = ""
        if len(self.descendants) > 0:
            desc_strs = "\n".join([x.to_org(media_dir) for x in self.descendants])
            descendants = "*** Descendants\n{}".format(desc_strs)

        media = "*** Media\n{}".format(self.media_to_org(media_dir))
        links = "*** Links\n{}".format("\n".join(set(self.links())))


        return "{}{}{}{}{}{}\n".format(header,
                                       ancestors,
                                       tweet,
                                       descendants,
                                       media,
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
                raise Exception("File already exists: {} {}".format(x, y))
            copyfile(x, y)

    def check_hashes(self, a, b):
        a_hash = ""
        b_hash = "5"
        with open(abspath(a), 'rb') as f:
            a_hash = sha256(f.read()).hexdigest()
        with open(abspath(b), 'rb') as f:
            b_hash = sha256(f.read()).hexdigest()
        return a_hash == b_hash


def conversation_p(tag):
    cls = tag['class']
    tc = "ThreadedConversation" in cls
    tcs = "ThreadedConversation--selfThread" in cls
    lt = "ThreadedConversation--loneTweet" in cls
    return tc and not (tcs or lt)
