"""
Parse Scarfolk html files into org files
"""

#imports
from bs4 import BeautifulSoup
from urllib.parse import unquote
from os import listdir, mkdir
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os.path import splitext, split
from shutil import copyfile
from hashlib import sha256
from os.path import expanduser, abspath
import argparse
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

tag_gap = " " * 80
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser("")
parser.add_argument("-s", "--source")
parser.add_argument("-o", "--output")

args = parser.parse_args()
args.source = abspath(expanduser(args.source))
args.output = abspath(expanduser(args.output))

if not exists(args.output):
    mkdir(args.output)


def file_to_hash(filename):
    with open(abspath(expanduser(filename)), 'br') as f:
        return sha256(f.read()).hexdigest()

#get the htmls
htmls = [x for x in listdir(args.source) if splitext(x)[1] == '.html']

tag_set = set()
post_groups  = []
#for each:
for page in htmls:
    logging.info("Loading: {}".format(page))
    extracted_data = []
    with open(join(args.source, page), 'r') as f:
        html = BeautifulSoup(f.read(), 'html.parser')

    main = html.find("div", id="Blog1")
    posts = main.find_all("div", class_="date-outer")

    post_group = []
    date_group = None
    for post in posts:
        date = post.find("h2", class_="date-header").get_text(strip=True)
        if date_group is None:
            split_date = date.split(" ")
            date_group = " ".join(split_date[-2:])
            logging.info("Determined as: {}".format(date_group))
        title = post.find("h3", class_="post-title").get_text(strip=True)
        logging.debug("Dealing with {}".format(title))
        post_body = post.find("div", class_="post-body")
        body_text = post_body.get_text(strip=True)
        imgs = [unquote(x['src']) for x in post_body.find_all("img")]
        footer = post.find("div", class_="post-footer-line-2")
        tags = [x.get_text(strip=True) for x in footer.find_all("a")]
        tag_set.update(tags)

        post_data = (date, title, body_text, imgs, tags)
        post_group.append(post_data)

    post_groups.append((date_group, post_group))


def post_to_org(post, new_loc):
    date, title, body, imgs, tags = post
    tag_str = ""
    if bool(tags):
        tag_str = ":{}:".format(":".join([x.replace(" ","_") for x in tags]))
    date_block = ":DATE:\n{}\n:END:".format(date)
    new_img_locs = [join(new_loc, split(x)[1]) for x in imgs]
    img_links = ["[[file:{}][{}]]".format(x, split(x)[1]) for x in new_img_locs]
    img_block = "*** Images\n {}\n".format("\n".join(img_links))


    result = "** {}{}{}\n{}\n{}\n{}\n".format(title,
                                              tag_gap,
                                              tag_str,
                                              date_block,
                                              body,
                                              img_block)

    return result, img_links, tag_str


# output into org files for each month/year combo
logging.info("Writing out files")
only_imgs = []
for date_text, posts in post_groups:
    assert(not exists(join(args.output, "{}.org".format(date_text))))
    new_img_loc = join("{}_files".format(date_text))
    mkdir(join(args.output, new_img_loc))

    post_text = []
    for post in posts:
        p, new_imgs, tags = post_to_org(post, new_img_loc)
        post_text.append(p)
        only_imgs.append((new_imgs, tags))

    with open(join(args.output, "{}.org".format(date_text)), 'w') as f:
        f.write("\n".join(post_text))

    #move all the files:
    for post in posts:
        imgs = post[3]
        adjusted_locs = [join(args.output, new_img_loc, split(x)[1]) for x in imgs]
        for old_loc, new_loc in zip(imgs, adjusted_locs):
            if not exists(join(args.output, new_loc)):
                copyfile(join(args.source, old_loc), join(args.output, new_loc))
            else:
                sha1 = file_to_hash(join(args.source, old_loc))
                sha2 = file_to_hash(join(args.output, new_loc))
                assert(sha1 == sha2)

# output master tags list
logging.info("Writing master tag list")
with open(join(args.output, "master_tag_list") ,'w') as f:
    f.write("\n".join(tag_set))

# output image only + tags files
logging.info("Writing master image list")
with open(join(args.output, "master_img_list.org"), "w") as f:
    for new_imgs, tags in only_imgs:
        f.write("{}\n".format("\n".join(["** {}{}{}".format(x,tag_gap,tags) for x in new_imgs])))

