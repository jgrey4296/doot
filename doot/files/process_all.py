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

from doot.files.clean_dirs import clean_target_dirs

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

class ProcessAllTask:
    """
    Run a given function on all files from the globs,
    putting returned text into build/processed/{name}

    process :: path -> str
    name_transform :: path -> str
    """

    def __init__(self, globs=None, process=None, name_transform=None, name="default", **kwargs):
        self.create_doit_tasks            = self.build
        self.output_dir                   = build_dir / "processed" / name
        self.process                      = process
        self.name_transform               = name_transform
        self.globs                        = globs
        self.kwargs                       = kwargs
        self.default_spec                 = { "basename" : f"process_all::{name}" }
        self.glob_results : list[pl.Path] = []

    def uptodate(self):
        """ run the globs, and check theres an output file for each input file """
        return True

    def mkdir(self):
        try:
            self.output_dir.mkdir()
        except FileExistsError:
            print(f"{x} already exists")
            pass



    def run_globs(self):
        """ run the globs and check theres files to process  """
        self.glob_results = []
        base = pl.Path('.')
        for glob in self.globs:
            self.glob_results += list(base.glob(glob))

        if not bool(self.glob_results):
            return False

        return True

    def run_process(self):
        """ Run the process on each globbed file,
        and store output in the transformed output file name
        """
        for path in self.glob_results:
            outfile_name : str = self.name_transform(path)
            try:
                result = self.process(path)
            except Exception as err:
                result = str(err)

            with open(self.output_dir / outfile_name, 'w') as f:
                f.write(result)


    def build(self):
        task_desc = self.default_spec.copy()
        task_desc.update(self.kwargs)
        task_desc.update({
            "actions"  : [ self.run_globs, self.mkdir, self.run_process ],
            "targets"  : [ self.output_dir ],
            "task_dep" : [ "_checkdir::process_all" ],
            "uptodate" : [ self.uptodate ],
            "clean"    : [ clean_target_dirs],
        })
        yield task_desc



##-- checkdir
check_proc = CheckDir(build_dir / "processed", name="process_all", task_dep=["_checkdir::build"])
##-- end checkdir
