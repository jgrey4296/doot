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

from doot import tasker

class ClipsRun(tasker.DootTasker):
    """
    Run a clips rulebase
    """
    pass

class CoqBuild(tasker.DootTasker):
    """
    Build and run coq files
    """
    pass

class ErlangVMBuild(tasker.DootTasker):
    """
    https://rebar3.org/docs/getting-started/
    https://hex.pm/docs/usage
    https://hexdocs.pm/mix/Mix.html
    """
    pass

class GruntRun(tasker.DootTasker):
    """
    https://gruntjs.com/getting-started
    """
    pass

class CabalBuild(tasker.DootTasker):
    """
    a thin utility layer on top of cabal
    """
    pass

class BrewBuild(tasker.DootTasker):
    """
    https://brew.sh
    """
    pass

class DotNetVMCompile(tasker.DootTasker):
    """
    use mono's mcs for compiling
    use xbuild on linux,
    mxbuild on windows
    to build csharp projects
    """
    pass

class CombinePDFTask(globber.DootEagerGlobber):
    """
    Combine pdfs
    For pdfs in directories,
    concatenate them into one
    """
    pass

class SamplePDFTask(globber.DootEagerGlobber):
    """
    sample pdfs
    For PDFs in each directory, get their leading n pages,
    and build a summary pdf
    """
    pass

class PDFMetaData(globber.DootEagerGlobber):
    """
    pdf metadata
    build metadata summaries of found pdfs
    """
    pass

class PoetryBuild(tasker.DootTasker):
    """
    https://python-poetry.org/docs/cli/
    """
    pass

class PythonCompile(DootTasker, CommanderMixin):
    """
    https://pyinstaller.org/en/stable/
    Use pyinstaller to create an exe
    pyinstaller --collect-all tkinterdnd2 -w sub_processor.py
    """
    collect_libs  : Final[list] = doot.config.on_fail([], list).python.compile.collect()

    def __init__(self, name="python::compile", locs=None):
        super().__init__(name, locs)
        self.locs.ensure("build", "temp", "src", task=name)

    def set_params(self):
        return [
            { "name" : "output",
                "short" : "o",
                "type" : str,
                "default": "--onedir",
                "choices" : [("--onefile", ""),
                             ("--onedir", ""),

                             ],
              }
        ]

    def task_detail(self, task):
        task.update({
            "actions" : [ self.make_cmd(self.build_cmd) ],
        })
        return task

    def build_cmd(self):
        args = [ "pyinstaller",
                 "--distpath", self.locs.build,
                 "--workpath", self.locs.temp,
                 "--name", self.locs.src.name,
                 ]
        #  --add-data
        #  --paths

        if bool(collect_libs):
            args.append("--collect-all")
            args += collect_libs
        args.append("-w")
        args.append(self.locs.src)
        return args

class GemBuild(tasker.DootTasker):
    """
    https://guides.rubygems.org/
    """
    pass

class SCLangRun(tasker.DootTasker):
    """
    fork an SCLang server
    """
    pass

class SoarBuild(tasker.DootTasker):
    """
    Run a soar agent
    """
    pass

class Z3Builder(tasker.DootTasker):
    """
    Solve a problem using Z3
    """
    pass
