"""
Integrates newly parsed twitter->org files
into the existing set
"""
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir, mkdir
from subprocess import call
from random import choice
import argparse
import logging as root_logger

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU

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
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join(["Integrate newly parsed twitter orgs into the existing library"]))
    parser.add_argument('-s', '--source', action="append")
    parser.add_argument('-l', '--library', action="append")
    parser.add_argument('-e', '--exclude', action="append")
    parser.add_argument('-G', '--groupless', action="store_true")


    args         = parser.parse_args()
    args.source  = [abspath(expanduser(x)) for x in args.source]
    args.library = [abspath(expanduser(x)) for x in args.library]
    if args.exclude is None:
        args.exclude = []

    args.exclude = [abspath(expanduser(x)) for x in args.exclude]

    if any([not exists(x) for x in args.source + args.library]):
        raise Exception('Source and Output need to exist')

    #load the newly parsed org names
    # { file_name : parent_path }
    newly_parsed = {}
    for source in args.source:
        if isfile(source):
            newly_parsed[split(source)[1]] = source
        else:
            found = {x : source for x in listdir(source) if splitext(x)[1] == '.org'}
            newly_parsed.update(found)


    logging.info("Newly parsed to transfer: {}".format(len(newly_parsed)))

    #get the existing org names, as a dict with its location
    existing_orgs = {}
    queue = args.library[:]
    while queue:
        current = queue.pop(0)
        if current in args.exclude:
            continue
        if isdir(current):
            queue += [join(current,x) for x in listdir(current)]
        elif splitext(current)[1] == ".org":
            existing_orgs[split(current)[1]] = split(current)[0]

    logging.info("Existing orgs: {}".format(len(existing_orgs)))

    totally_new = []
    #now update existing with the new

    for x in newly_parsed:
        if x not in existing_orgs:
            logging.info("Found a completely new user: {}".format(x))
            totally_new.append(x)
            continue

        logging.info("Integrating: {}".format(x))
        new_org        = join(newly_parsed[x], x)
        new_files      = join(newly_parsed[x], "{}_files".format(splitext(x)[0]))
        existing_org   = join(existing_orgs[x], x)
        existing_files = join(existing_orgs[x], "{}_files".format(splitext(x)[0]))

        with open(new_org, 'r') as f:
            lines = f.read()

        with open(existing_org, 'a') as f:
            f.write("\n")
            f.write(lines)

        for y in listdir(new_files):
            if not isfile(join(new_files, y)):
                continue
            call_sig = ['cp', join(new_files, y), existing_files]
            call(call_sig)

    logging.info("Completely new to transfer: {}".format(len(totally_new)))

    # Now copy completely new files
    for x in totally_new:
        logging.info("Adding to library with: {}".format(x))
        file_name = join(newly_parsed[x], x)
        file_dir  = join(newly_parsed[x], "{}_files".format(splitext(x)[0]))

        first_letter = x[0].lower()
        if not ("a" <= first_letter <= "z"):
            first_letter = "symbols"

        target_for_new = join(args.library[0],"group_{}".format(first_letter))
        if args.groupless:
            target_for_new = args.library[0]

        call(['cp', file_name, target_for_new])
        call(['cp' ,'-r' ,file_dir, target_for_new])
