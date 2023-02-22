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
                    cast, final, overload, runtime_checkable, Final)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

END_LINE : Final = "---%%%--- Finished"

def file_is_finished(path) -> bool:
    result = False
    if not path.exists():
        return result

    response = subprocess.run(['tail', '-n', '1', str(path)],
                              capture_output=True,
                              shell=False)
    line = response.stdout.decode()
    if line == END_LINE:
        result = True

    return result

def exiftool_pdf_md(path) -> str:
    result = ""
    try:
        response = subprocess.run(["exiftool", str(path), "-PDF:all"],
                                  capture_output=True,
                                  shell=False)
        result = response.stdout.decode() if response.returncode == 0 else response.stderr.decode()

    except Exception as err:
        result = str(err)

    return result

def exiftool_xmp_md(path) -> str:
    result = ""
    try:
        response = subprocess.run(["exiftool", str(path), "-XMP:all"],
                                  capture_output=True,
                                  shell=False)
        result = response.stdout.decode() if response.returncode == 0 else response.stderr.decode()

    except Exception as err:
        result = str(err)

    return result

def pdftk_md(path) -> str:
    result = ""
    try:
        response = subprocess.run(["pdftk", str(path), "dump_data_utf8"],
                                  capture_output=True,
                                  shell=False)
        result = response.stdout.decode() if response.returncode == 0 else response.stderr.decode()

        result = "\n".join([x for x in result.split("\n") if "Info" in x])

    except Exception as err:
        result = str(err)

    return result
