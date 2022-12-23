#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
##-- end imports


def clean_target_dirs(task, dryrun):
    """ Clean targets, including non-empty directories
    Add to a tasks 'clean' dict value
    """
    if dryrun:
        print("%s - dryrun removing '%s'" % (task.name, task.targets))
        return

    force_tree = task.meta is not None and "force_clean" in task.meta

    for target_s in sorted(task.targets, reverse=True):
        try:
            target = pl.Path(target_s)
            if not target.exists():
                print("%s - N/A '%s'" % (task.name, target))
                continue

            if target.is_file():
                print("%s - removing '%s'" % (task.name, target))
                target.remove()
            elif target.is_dir() and not bool([x for x in target.iterdir() if x.name != ".DS_Store"]):
                print("%s - removing tree '%s'" % (task.name, target))
                shutil.rmtree(str(target))
            elif target.is_dir() and force_tree:
                print("%s - force removing tree '%s'" % (task.name, target))
                shutil.rmtree(str(target))
            else:
                contains = " ".join(str(x) for x in target.iterdir())
                print("%s - not empty: %s : %s" % (task.name, target, contains))
        except OSError as err:
            print(err)
