##-- imports
from __future__ import annotations
import pathlib as pl
import shutil

##-- end imports


def force_clean_targets(task, dryrun):
    """ Clean targets, including non-empty directories
    Add to a tasks 'clean' dict value
    """
    for target_s in sorted(task.targets, reverse=True):
        try:
            target = pl.Path(target_s)
            if dryrun:
                print("%s - dryrun removing '%s'" % (task.name, target))
                continue

            print("%s - removing '%s'" % (task.name, target))
            if target.is_file():
                target.remove()
            elif target.is_dir():
                shutil.rmtree(str(target))
        except OSError as err:
            print(err)
