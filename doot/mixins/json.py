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
import json

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import JsonParser
from typing import List

class JsonMixin:

    def json_load(self, fpath):
        return json.loads(fpath.read_text())

    def json_new_parser(self):
        return JsonParser(context=XmlContext())

    def json_load_using_gencode(self, fpath, parser, root_object=None, is_list=False):
        target_type = List[root_object] if is_list else root_object
        return parser.parse(filename, target_type)

    def json_filter(self, target, filter_str="."):
        """
        outputs to process' stdout
        """
        return ["jq", "-M", "S", filter_str, target]

    def json_schema(self, target, package="genJson"):
        """ writes output to stdout """
        args = ["xsdata", "generate",
                ("--recursive" if target.is_dir() else ""),
                "-p", package,
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                target
            ]

        return list(filter(bool, args))

    def json_plantuml(self, dst, src):
        """
        writes to dst
        """
        header   = "@startjson\n"
        footer   = "\n@endjson\n"

        with open(pl.Path(targets[0]), 'w') as f:
            f.write(header)
            f.write(fpath.read_text())
            f.write(footer)

    def xsdata_generate(self, targets:list, package:str):
        """ TODO import and call xsdata directly
        using targets as URI's, into an xsdata.codegen.transformer.SchemaTransformer
        """
        from xsdata.models.config import GeneratorConfig
        from xsdata.codegen.transformer import SchemaTransformer

        config                = GeneratorConfig.read(config_file)
        config.output.package = package

        transformer           = SchemaTransformer(config=config, print=stdout)
        uris                  = sorted(map(pl.Path.as_uri, targets))
        transformer.process(uris)
