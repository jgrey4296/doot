"""
Simple Utility to convert pdf library to text
"""
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
from subprocess import call
import argparse

# Setup root_logger:
from os.path import splitext, split
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

def find_files(start):
    logging.info("Finding pdfs in {}".format(start))
    queue = [start]
    files = []
    while bool(queue):
        current = queue.pop(0)
        if isdir(current):
            queue += [join(current,x) for x in listdir(current)]
        elif isfile(current) and splitext(current)[1] == ".pdf":
            files.append(current)

    logging.info("Found {} pdfs".format(len(files)))
    return files

def convert_pdfs_to_text(files):
    logging.info("Converting {} files".format(len(files)))
    for x in files:
        path = split(x)[0]
        name = splitext(split(x)[1])[0]
        text_file = join(path,".{}.txt".format(name))
        if exists(text_file):
            continue

        call_sig = ['pdftotext', x, text_file]
        logging.info("Converting: {}".format(" ".join(call_sig)))
        call(call_sig)

def convert_alternative(source, output_dir, title):
    target = "{}.txt".format(title)
    logging.info("Converting {} from {}".format(target, source))
    subprocess.run(['mutool',
                    'convert',
                    '-F', 'text',
                    '-o', join(output_dir, target),
                    source],
                   stdout=subprocess.PIPE)


if __name__ == "__main__":
    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join([""]))
    parser.add_argument('-l', '--library')

    args = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    files = find_files(args.library)
    convert_pdfs_to_text(files)
