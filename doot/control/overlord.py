"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import sys
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
# from uuid import UUID, uuid1
# from weakref import ref

# from bs4 import BeautifulSoup
# import boltons
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
# import more_itertools as itzplus
# import networkx as nx
# import numpy as np
# import pandas
# import pomegranate as pom
# import pony import orm
# import pronouncing
# import pyparsing as pp
# import rich
# import seaborn as sns
# import sklearn
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
# import spacy # nlp = spacy.load("en_core_web_sm")

##-- end imports

from importlib.metadata import EntryPoint
import tomler
import doot
import doot.constants
from doot._abstract.overload import DootOverlord_i
from doot._abstract.loader import CommandLoader_i, TaskLoader_i
from doot._abstract.tasker import DootTasker_i
from doot._abstract.parser import DootParser_i, DootParamSpec
from doot._abstract.task import DootTask_i
from doot._abstract.current_cmd import DootCommand_i

from doot.overlord import DootOverlord_i
from doot.loaders.plugin_loader import DootPluginLoader
from doot.errors import DootParseError, DootInvalidConfig

class DootOverlord(DootOverlord_i):

    @staticmethod
    def print_version():
        """print doot version (includes path location)"""
        print("Doot Version: %s", doot.__version__)
        print("lib @", os.path.dirname(os.path.abspath(__file__)))

    def __init__(self, *, loaders:dict[str, Loader_i]=None, config_filenames:tuple=('doot.toml', 'pyproject.toml'), extra_config:dict|Tomler=None, args:list=None):
        logging.debug("Initialising Overlord")
        self.args           = args or sys.argv[:]
        self.BIN_NAME       = self.args[0].split('/')[-1]
        self.loaders        = loaders
        self.doot_arg_specs = [
            DootParamSpec(name="version")
        ]

        self.plugins     : dict               = {}
        self.current_cmd : DootCommand_i      = None
        self.taskers     : list[DootTasker_i] = []

        self.load_plugins()
        self.load_commands()
        self.load_taskers()
        self.parse_args()
        logging.debug("Core Overlord Initialisation complete")

    def load_plugins(self):
        self.plugin_loader    = (self.loaders.get('plugin', None) or DootPluginLoader()).setup(extra_config)
        self.plugins : Tomler = self.plugin_loader.load()

    def load_commands(self):
        specified_cmd_loader = config.on_fail("default").command_loader()
        match (self.loaders.get("command", None), self.plugins.get("command_loader", [])):
            case None, []:
                raise KeyError("No Command Loader found")
            case CommandLoader_i as l, _:
                self.cmd_loader = l
            case None, [EntryPoint()] as l:
                self.cmd_loader = l.load()()
            case None, [*_] as loaders:
                matching_loaders = [x for x in loaders if x.name == specified_cmd_loader]
                if not bool(matching_loaders):
                    raise KeyError("No Matching Command Loader found: ", specified_cmd_loader)
                loaded = matching_loaders[0].load()()
                self.cmd_loader = loaded

        if self.cmd_loader is None:
            raise TypeError("Command Loader is not initialised")
        if not isinstance(self.cmd_loader, CommandLoader_i):
            raise TypeError("Attempted to use a non-Commandloader_i as a CommandLoader: " self.cmd_loader)

        self.cmd_loader.setup(self.plugins)
        self.cmds = self.cmd_loader.load()

    def load_taskers(self):
        specified_task_loader = config.on_fail("default").task_loader()
        match (self.loaders.get("task", None), self.plugins.get("task_loader", [])):
            case None, []:
                raise KeyError("No task Loader found")
            case TaskLoader_i as l, _:
                self.task_loader = l
            case None, [EntryPoint()] as l:
                self.task_loader = l.load()()
            case None, [*_] as loaders:
                matching_loaders = [x for x in loaders if x.name == specified_task_loader]
                if not bool(matching_loaders):
                    raise KeyError("No Matching Task Loader found: ", specified_task_loader)
                loaded = matching_loaders[0].load()()
                self.task_loader = loaded

        if self.task_loader is None:
            raise TypeError("Task Loader is not initialised")
        if not isinstance(self.task_loader, TaskLoader_i):
            raise TypeError("Attempted to use a non-Commandloader_i as a CommandLoader: " self.cmd_loader)

        self.task_loader.setup(self.plugins)
        self.taskers = self.task_loader.load()

    def parse_args(self, args=None):
        specified_parser = config.on_fail("default").parser()
        match self.plugins.get("parser", [])):
            case []:
                raise KeyError("No parser found")
            case [EntryPoint()] as l:
                self.parser = l.load()()
            case [*_] as parsers:
                matching_parsers = [x for x in parsers if x.name == specified_parser]
                if not bool(matching_parsers):
                    raise KeyError("No Matching parser found: ", specified_parser)
                loaded = matching_loaders[0].load()()
                self.arg_parser = loaded

        if not isinstance(self.arg_parser, DootArgParser_i):
            raise TypeError("Improper argparser specified: ", self.arg_parser)

        doot.args = self.arg_parser.parse(args or self.args, self.doot_arg_specs, self.cmds, self.tasks)


    def __call__(self, cmd=None):
        logging.debug("Overlord Calling: %s" cmd or doot.args.cmd.name)
        target = (cmd
            or doot.args.on_fail(None).cmd.name()
            or doot.constants.default_cli_cmd)

        self.current_cmd = self.cmds.get(target, None)
        if self.current_cmd is None:
            logging.error("Specified Command Couldn't be Found: %s", target)
            return

        self.current_cmd(self.taskers, self.plugins)
