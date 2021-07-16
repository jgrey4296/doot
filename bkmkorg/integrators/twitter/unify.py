#!/opt/anaconda3/envs/bookmark/bin/python
"""
Integrates newly parsed twitter->org files
into the existing set
"""
import argparse
import logging as root_logger
from os import listdir, mkdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from random import choice
from subprocess import call

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.file import retrieval

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

def copy_files(source_dir, target_dir):
    logging.info(f"Copying from {source_dir} to {target_dir}")
    if exists(source_dir) and not exists(target_dir):
        logging.info("as group")
        call(['cp' ,'-r' ,source_dir, target_dir])
    elif exists(source_dir):
        logging.info("as individual")
        for y in listdir(source_dir):
            if not isfile(join(source_dir, y)):
                continue

            call_sig = ['cp', join(source_dir, y), join(target_dir, y)]
            call(call_sig)


def copy_new(source, lib_path):
    logging.info(f"Adding to library with: {source}")
    file_name = split(source)[1]
    no_ext = splitext(file_name)[0]
    file_dir  = join(split(source)[0], f"{no_ext}_files")

    first_letter = file_name[0].lower()
    if not ("a" <= first_letter <= "z"):
        first_letter = "symbols"

    target_for_new = join(lib_path,f"group_{first_letter}")

    if not exists(join(target_for_new, file_name)):
        call(['cp', source, target_for_new])

    copy_files(file_dir, join(target_for_new, f"{no_ext}_files"))


def integrate(source, lib_dict):
    logging.info(f"Integrating: {source}")
    just_org = split(source)[1]
    just_source_path = split(source)[0]
    just_name = splitext(just_org)[0]
    new_org        = source
    new_files      = join(just_source_path, f"{just_name}_files")
    existing_org   = join(lib_dict[just_org], just_org)
    existing_files = join(lib_dict[just_org], f"{just_name}_files")

    assert(exists(existing_org))
    if not exists(existing_files):
        mkdir(existing_files)

    with open(new_org, 'r') as f:
        lines = f.read()

    with open(existing_org, 'a') as f:
        f.write("\n")
        f.write(lines)

    if not exists(new_files):
        return

    copy_files(new_files, existing_files)


if __name__ == "__main__":
    # Setup
    args         = parser.parse_args()
    args.source  = [abspath(expanduser(x)) for x in args.source]
    args.library = [abspath(expanduser(x)) for x in args.library]
    if args.exclude is None:
        args.exclude = []

    args.exclude = [abspath(expanduser(x)) for x in args.exclude]

    if any([not exists(x) for x in args.source + args.library]):
        raise Exception('Source and Output need to exist')

    #load the newly parsed org names
    # { file_name : full_path }
    newly_parsed = retrieval.get_data_files(args.source, ext=".org")

    logging.info("Newly parsed to transfer: {}".format(len(newly_parsed)))

    #get the existing org names, as a dict with its location
    library_orgs = retrieval.get_data_files(args.library, ext=".org")
    existing_orgs = {}
    for lib_org in library_orgs:
        if lib_org in args.exclude:
            continue

        existing_orgs[split(lib_org)[1]] = split(lib_org)[0]

    logging.info("Existing orgs: {}".format(len(existing_orgs)))

    totally_new = []
    #now update existing with the new

    for x in newly_parsed:
        if split(x)[1] not in existing_orgs:
            logging.info("Found a completely new user: {}".format(x))
            totally_new.append(x)
            continue

        integrate(x, existing_orgs)

    logging.info("Completely new to transfer: {}".format(len(totally_new)))

    # Now copy completely new files
    for x in totally_new:
        copy_new(x, args.library[0])
