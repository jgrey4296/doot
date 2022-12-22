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

    for target_s in sorted(task.targets, reverse=True):
        try:
            target = pl.Path(target_s)
            print("%s - removing '%s'" % (task.name, target))
            if target.is_file():
                target.remove()
            elif target.is_dir() and not bool([x for x in target.iterdir() if x.name != ".DS_Store"]):
                shutil.rmtree(str(target))
            else:
                print(f"Dir {target} is not empty: {list(target.iterdir())}")
        except OSError as err:
            print(err)
