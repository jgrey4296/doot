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

class XMLMixin:

    xsdata_defaults = [ "--relative-imports", "--postponed-annotations", "--kw-only", "--frozen", "--no-unnest-clases"]

    def xml_elements(self, targets):
        """
        ouputs to process' stdout
        build an `xml el` command of all available xmls
        http://xmlstar.sourceforge.net/
        """
        return ["xml", "el", "-u"] + targets

    def xml_trang(self, fpath, targets:list):
        """
        outputs to fpath
        trang  : https://relaxng.org/jclark/ [-C catalogFileOrUri] [-I rng|rnc|dtd|xml] [-O rng|rnc|dtd|xsd] [-i input-param] [-o output-param] inputFileOrUri ... outputFile
        """
        assert(all([x.suffix == ".xml" for x in targets])), "Trang only accepts .xml files"
        return ["trang"] + targets

    def xml_xsd(self, fpath, targets):
        """
        generates to fpath
        xsd    : mono
        """
        return ["xsd"] + targets + ["/o", fpath]

    def xml_xsdata(self, fpath, target, recursive=False, package_name="genxml"):
        """
        generates to fpath
        xsdata : https://github.com/tefra/xsdata
        """
        xsdata_args = and_args or self.xsdata_defaults
        return ["xsdata", "generate"] + xsdata_args

    def xsml_plantuml(self, target):
        """
        outputs to process' stdout
        """
        return ["xsdata", "generate", "-o", "plantuml", "-pp", target]

    def xml_format(self, target):
        """
        outputs to process' stdout
        """
        args = ["xml" , "fo",
            "-s", "4",     # indent 4 spaces
            "-R",          # Recover
            "-N",          # remove redundant declarations
            "-e", "utf-8", # encode in utf-8
        ]
        if target.suffix in [".html", ".xhtml", ".htm"]:
                args.append("--html")

        args.append(target)
        return args

    def xml_validate(self, targets:list, xsd):
        """
        outputs to process' stdout
        """
        args = ["xml", "val",
                "-e",    # verbose errors
                "--net", # net access
                "--xsd"  # xsd schema
                ]
        args.append(self.xsd)
        args += targets
        return args
