#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import zipfile
import doot

zip_default_name = doot.config.on_fail("default", str).tool.doot.zip.name()
zip_overwrite    = doot.config.on_fail(False, bool).tool.doot.zip.overwrite()
zip_compression  = doot.config.on_fail("ZIP_DEFLATED", str).tool.doot.zip.compression(wrapper=lambda x: getattr(zipfile, x))
zip_level        = doot.config.on_fail(4, int).tool.doot.zip.level()

class ZipperMixin:
    zip_name       = zip_default_name
    zip_overwrite  = zip_overwrite
    zip_root       = None
    compression    = zip_compression
    compress_level = zip_level

    def zip_set_root(self, fpath):
        self.zip_root = fpath

    def zip_create(self, fpath):
        assert(fpath.suffix== ".zip")
        if self.zip_overwrite and fpath.exists():
            fpath.unlink()
        elif fpath.exists():
            return

        logging.info("Creating Zip File: %s", fpath)
        now = datetime.datetime.strftime(datetime.datetime.now(), "%Y:%m:%d::%H:%M:%S")
        record_str = f"Zip File created at {now} for doot task: {self.base}"

        with zipfile.ZipFile(fpath, mode='w', compression=self.compression, compresslevel=self.compress_level, allowZip64=True ) as targ:
            targ.writestr(".taskrecord", record_str)

    def zip_add_paths(self, fpath, *args):
        """
        Add specific files to the zip
        """
        logging.info("Adding to Zipfile: %s : %s", fpath, args)
        assert(fpath.suffix == ".zip")
        root = self.zip_root or pl.Path()
        paths = [pl.Path(x) for x in args]
        with zipfile.ZipFile(fpath, mode='a',
                             compression=self.compression, compresslevel=self.compress_level,
                             allowZip64=True ) as targ:
            for file_to_add in paths:
                try:
                    relpath = file_to_add.relative_to(root)
                    attempts = 0
                    write_as = relpath
                    while str(write_as) in targ.namelist():
                        if attempts > 10:
                            logging.warning(f"Couldn't settle on a de-duplicated name for: {file_to_add}")
                            break
                        logging.debug(f"Attempted Name Duplication: {relpath}", file=sys.stderr)
                        write_as = relpath.with_stem(f"{relpath.stem}_{hex(randint(1,100))}")
                        attempts += 1

                    targ.write(str(file_to_add), write_as)

                except ValueError:
                    relpath = root / pl.Path(file_to_add).name
                except FileNotFoundError as err:
                    logging.warning(f"Adding File to Zip {fpath} failed: {err}", file=sys.stderr)

    def zip_globs(self, fpath, *globs):
        """
        Add files chosen by globs to the zip, relative to the cwd
        """
        logging.debug(f"Zip Globbing: %s : %s", fpath, globs)
        assert(fpath.suffix == ".zip")
        cwd  = pl.Path()
        root = self.zip_root or cwd
        with zipfile.ZipFile(fpath, mode='a',
                             compression=self.compression, compresslevel=self.compress_level,
                             allowZip64=True) as targ:
            for glob in globs:
                result = list(cwd.glob(glob))
                logging.info(f"Globbed: {cwd}[{glob}] : {len(result)}")
                for dep in result:
                    try:
                        if dep.stem[0] == ".":
                            continue
                        relpath = pl.Path(dep).relative_to(root)
                        targ.write(str(dep), relpath)
                    except ValueError:
                        relpath = root / pl.Path(dep).name
                    except FileNotFoundError as err:
                        logging.warning(f"Adding File to Zip {fpath} failed: {err}", file=sys.stderr)

    def zip_add_str(self, fpath, fname, text:str):
        assert(fpath.suffix == ".zip")
        with zipfile.ZipFile(fpath, mode='a',
                             compression=self.compression, compresslevel=self.compress_level,
                             allowZip64=True) as targ:
            assert(fname not in targ.namelist())
            targ.writestr(fname, text)
