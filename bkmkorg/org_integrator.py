"""
Integrates newly parsed twitter->org files
into the existing set
"""

from os.path import join, isfile, exists, isdir, splitext, expanduser
from os import listdir, mkdir
from subprocess import call
from random import choice
import argparse

parser = argparse.ArgumentParser("")
parser.add_argument('-s', '--source')
parser.add_argument('-o', '--output')
parser.add_argument('-n', '--newgroup', action='store_true')

args = parser.parse_args()

if any([not exists(x) for x in [args.source, args.output]]):
    raise Exception('Source and Output need to exist')

#load the newly parsed org names
newly_parsed = []
if isfile(args.source):
    newly_parsed = [args.source]
else:
    newly_parsed = [x for x in listdir(args.source) if splitext(x)[1] == '.org']

logging.info("Newly parsed to transfer: {}".format(len(newly_parsed)))

#get the existing org names, as a dict with its location
existing_orgs = {}
for x in [x for x in listdir(args.output) if isdir(x)]:
    current = join(args.output, x)
    orgs = {y: current for y in listdir(current) if splitext(y)[1] == '.org'}
    existing_orgs.update(orgs)

logging.info("Existing orgs: {}".format(len(existing_orgs)))

#now update existing with the new
totally_new = []
for x in newly_parsed:
    if x not in existing_orgs:
        logging.info("Found a completely new user: {}".format(x))
        totally_new.append(x)
        continue

    new_org = join(args.source, x)
    new_files = join(args.source, "{}_files".format(splitext(x)[0]))
    existing_org = join(existing_orgs[x], x)
    files_dir_name = "{}_files".format(splitext(x)[0])
    existing_files = join(existing_orgs[x], files_dir_name)

    with open(new_org, 'r') as f:
        discard = f.readline()
        lines = f.read()

    with open(existing_org, 'a') as f:
        f.write(lines)

    call(['cp', join(new_files, '*'), existing_files])

logging.info("Completely new to transfer: {}".format(len(totally_new)))
#then move completely new to a new directory
target_for_new = None
if bool(totally_new) and args.newgroup:
    new_group_num = len([x for x in listdir(args.output) if isdir(x)])
    target_for_new = join(args.output, "group_{}".format(new_group_num))
    logging.info("Making new group: {}".format(target_for_new))
    assert(not isdir(target_for_new))
    mkdir(target_for_new)
else:
    potential_groups = [x for x in listdir(args.output) if isdir(x)]
    target_for_new = join(args.output, choice(potential_groups))
    logging.info("Reusing group: {}".format(target_for_new))

for x in totally_new:
    logging.info("Dealing with: {}".format(x))
    file_name = join(args.source, x)
    file_dir = join(args.source, "{}_files".format(splitext(x)[0]))

    call(['cp', file_name, target_for_new])
    call(['cp' ,'-r' ,file_dir, target_for_new])
