"""
Cluster a mass of images together
"""
from PIL import Image
from random import shuffle
from os import mkdir
from shutil import copyfile
import argparse
from os import listdir
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os.path import splitext, split
from sklearn.cluster import KMeans
import PIL
import logging as root_logger
import numpy as np

EXTS = [".jpg",".jpeg",".png",".gif",".webp",".tiff"]
THUMB = (200,200)

def get_imgs(path):
    queue = [path]
    found = []
    while bool(queue):
        current = queue.pop(0)
        if isdir(current):
            queue += [join(current,x) for x in listdir(current)]
        elif splitext(current)[1].lower() in EXTS:
            found.append(current)

    return found

def load_img(path):
    try:
        img = Image.open(path)
        img2 = img.convert('RGB')
        return img2
    except:
        return None

def norm_img(img):
    split_c1 = img.split()
    histograms = [np.array(x.histogram()) for x in split_c1]
    sums = [sum(x) for x in histograms]
    norm_c1 = [x/y for x,y in zip(histograms, sums)]
    return np.array(norm_c1).reshape((1,-1))


if __name__ == "__main__":
    # Setup
    LOGLEVEL = root_logger.DEBUG
    LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
    root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

    console = root_logger.StreamHandler()
    console.setLevel(root_logger.INFO)
    root_logger.getLogger('').addHandler(console)
    logging = root_logger.getLogger(__name__)
    ##############################
    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join([""]))
    parser.add_argument('--groups', default=3)
    parser.add_argument('--target', default="source")
    parser.add_argument('--output', default="output")
    parser.add_argument('--rand', default=-1)
    parser.add_argument('--slice', default=200)

    args = parser.parse_args()
    args.groups = int(args.groups)
    args.rand = int(args.rand)
    args.slice = int(args.slice)
    args.target = abspath(expanduser(args.target))
    args.output = abspath(expanduser(args.output))

    logging.info("Starting")
    img_paths = get_imgs(args.target)
    logging.info("Got {} images from {}".format(len(img_paths), args.target))
    if args.rand > 0:
        logging.info("Using {} for rand".format(args.rand))
        shuffle(img_paths)
        img_paths = img_paths[:args.rand]

    # Get norm'd 1d histograms in batches
    norms = None
    last = 0
    the_range = list(range(args.slice, len(img_paths), args.slice)) + [1 + len(img_paths)]
    for amnt in the_range:
        img_and_none = [load_img(x) for x in img_paths[last:amnt]]
        imgs = [x for x in img_and_none]
        logging.info("Loaded images {}-{}".format(last, amnt))
        last = amnt
        new_norms = np.row_stack([norm_img(x) if x is not None else np.zeros((1,768)) for x in imgs])
        try:
            if norms is None:
                norms = new_norms
            else:
                norms = np.row_stack((norms, new_norms))
        except:
            breakpoint()

    logging.info("Normalized {} images".format(len(norms)))
    logging.info("Clustering")

    # Use K-Means clustering on the histograms
    km = KMeans(n_clusters=args.groups)
    km.fit(norms)
    logging.info("Clustering")
    labels = [x for x in km.labels_]

    paired = zip(img_paths, labels)

    if not exists(args.output):
        mkdir(args.output)

    # copy images into groups
    for img,group_num in paired:
        group_name = join(args.output, "group_{}".format(group_num))
        if not exists(group_name):
            mkdir(group_name)

        logging.info("Moving to group {} : {}".format(group_num, img))
        copyfile(img, join(group_name, split(img)[1]))
