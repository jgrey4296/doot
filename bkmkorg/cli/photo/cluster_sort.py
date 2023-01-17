"""
Cluster a mass of images together
"""
##-- imports
# Setup
from __future__ import annotations

import argparse
import logging as root_logger
import pathlib as pl
from random import shuffle
from shutil import copyfile

import numpy as np
import PIL
from PIL import Image
from sklearn.cluster import KMeans
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join([""]))
parser.add_argument('--groups', default=3)
parser.add_argument('--target', default="source")
parser.add_argument('--output', default="output")
parser.add_argument('--rand', default=-1)
parser.add_argument('--slice', default=200)

##-- end argparse

# TODO get image extensions from config
THUMB = (200,200)


def load_img(path:pl.Path):
    try:
        img = Image.open(str(path))
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


##-- ifmain
if __name__ == "__main__":
    args        = parser.parse_args()
    args.groups = int(args.groups)
    args.rand   = int(args.rand)
    args.slice  = int(args.slice)
    args.target = pl.Path(args.target).expanduser().resolve()
    args.output = pl.Path(args.output).expanduser().resolve()


    if not args.output.exists():
        args.output.mkdir()

    logging.info("Starting")
    img_paths = get_data_files(args.target, ext=img_exts)
    logging.info("Got %s images from %s", len(img_paths), args.target)
    if args.rand > 0:
        logging.info("Using %s for rand", args.rand)
        shuffle(img_paths)
        img_paths = img_paths[:args.rand]

    # Get norm'd 1d histograms in batches
    norms     = None
    last      = 0
    the_range = list(range(args.slice, len(img_paths), args.slice)) + [1 + len(img_paths)]
    for amnt in the_range:
        img_and_none = [load_img(x) for x in img_paths[last:amnt]]
        imgs = [x for x in img_and_none]
        logging.info("Loaded images %s-%s", last, amnt)
        last = amnt
        new_norms = np.row_stack([norm_img(x) if x is not None else np.zeros((1,768)) for x in imgs])
        try:
            if norms is None:
                norms = new_norms
            else:
                norms = np.row_stack((norms, new_norms))
        except:
            breakpoint()

    logging.info("Normalized %s images", len(norms))
    logging.info("Clustering")
    # Use K-Means clustering on the histograms
    km     = KMeans(n_clusters=args.groups)
    km.fit(norms)
    labels = [x for x in km.labels_]
    paired = zip(img_paths, labels)
    logging.info("Finished Clustering")

    # copy images into groups
    for img,group_num in paired:
        group_name = args.output / f"group_{group_num}"
        if not group_name.exists():
            group_name.mkdir()

        logging.info("Moving to group %s : %s", group_num, img)
        copyfile(img, group_name / img.name)

##-- end ifmain
