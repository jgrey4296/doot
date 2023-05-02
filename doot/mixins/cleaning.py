#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import pathlib as pl
import shutil

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

py_cache_globs = ["**/*.pyc", "**/*.pyo", "**/.mypy_cache", "**/__pycache__", "**/flycheck_*.py"]
lisp_globs     = ["**/*.elc"]
mac_os_globs   = ["**/.DS_Store", "**/*~"]
java_globs     = ["**/*.class"]
log_globs      = ["**/log.*", "**/*.log"]

class CleanerMixin:

    @staticmethod
    def clean_target_dirs(task, dryrun):
        """ Clean targets, including non-empty directories
        Add to a tasks 'clean' dict value
        """
        if dryrun:
            logging.info("%s - dryrun removing '%s'" % (task.name, task.targets))
            return

        force_tree = task.meta is not None and "force_clean" in task.meta

        for target_s in sorted(task.targets, reverse=True):
            try:
                target = pl.Path(target_s)
                if not target.exists():
                    logging.debug("%s - N/A '%s'" % (task.name, target))
                    continue

                if target.is_file():
                    logging.debug("%s - removing '%s'" % (task.name, target))
                    target.remove()
                elif target.is_dir() and not bool([x for x in target.iterdir() if x.name != ".DS_Store"]):
                    logging.debug("%s - removing tree '%s'" % (task.name, target))
                    shutil.rmtree(str(target))
                elif target.is_dir() and force_tree:
                    logging.debug("%s - force removing tree '%s'" % (task.name, target))
                    shutil.rmtree(str(target))
                else:
                    contains = " ".join(map(str, target.iterdir()))
                    logging.debug("%s - not empty: %s : %s" % (task.name, target, contains))
            except OSError as err:
                logging.warning(err)
