"""
Script to parse SFAM html and create an org file of images with appropriate tags
"""
from bs4 import BeautifulSoup
from os.path import join, isfile, exists, isdir, splitext, expanduser, split, abspath
from os import listdir
from functools import partial
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

#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser("")
parser.add_argument('-s', '--source')
parser.add_argument('-o', '--output')

args = parser.parse_args()
args.source = abspath(expanduser(args.source))
args.output = abspath(expanduser(args.output))

#check html dir exists
assert(exists(join(args.source, 'html')))
#check img dir exists
assert(exists(join(args.source, 'images')))

#Get the htmls
htmls = [x for x in listdir(join(args.source, 'html')) if splitext(x)[1] == '.html']

#Get the imgs
img_types = ['.png', '.jpg', '.gif']
images = [x for x in listdir(join(args.source, 'images')) if splitext(x)[1] in img_types]

logging.info("Got {} HTMLs and {} IMAGEs".format(len(htmls), len(images)))

def is_class_x(x, tag):
    return tag.has_attr('class') and tag.get('class')[0] == x

def is_id_x(x, tag):
    return tag.has_attr('id') and tag.get('id') == x

#parse html, get tags and img,
data = []
tag_set = set()
for page in htmls:
    with open(join(args.source, 'html', page),'r') as f:
        html = BeautifulSoup(f.read(), 'html.parser')

    comic = html.find(partial(is_id_x, 'comic'))
    if comic is None:
        logging.info("No Comic in {}".format(page))
        continue
    img = comic.find('img')
    if img is None:
        logging.info("No Comic in {}".format(page))
        continue
    link = img.get('src')
    alt_text = img['alt']
    image_name = split(link)[1]
    if image_name not in images:
        logging.warning("Image missing: {}".format(image_name))
        continue

    tags_div = html.find(class_="tags")
    tags = tags_div.find_all('a')
    tag_texts = [x.get_text(strip=True).replace(" ","_") for x in tags]
    tag_set.update(tag_texts)

    title_list = list(html.find(class_="move-up heading").find('a', class_="title").strings)
    logging.info("Title list: {}".format(" | ".join(title_list)))
    title = title_list[0]
    date = html.find(class_="date").get_text(strip=True)

    image_path = join(args.source, 'images', image_name)
    data.append((title, image_path, alt_text, tag_texts, date))


#output to org file
tag_gap = " " * 80
with open(args.output, 'a') as f:
    for entry in data:
        title, img, alt, tags, date = entry
        date_string = "    :DATE:\n     {}\n    :END:\n\n".format(date)
        if bool(tags):
            tag_string = ":{}:".format(":".join(tags))
        else:
            tag_string = ""
        f.write("** [[{}][{}]]{}{}\n{}{}\n\n".format(img,
                                                     title,
                                                     tag_gap,
                                                     tag_string,
                                                     date_string,
                                                     alt))

with open(join(split(args.output)[0], "tag_list"), "w") as f:
    f.write("\n".join(tag_set))
