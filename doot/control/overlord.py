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
import sys
import time
import types
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

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

from importlib.metadata import EntryPoint

import doot
import doot.constants
import tomler
from doot._abstract import (ArgParser_i, Command_i, CommandLoader_p,
                            Overlord_p, Task_i, Tasker_i, TaskLoader_p)

from doot.errors import DootInvalidConfig, DootParseError
from doot.loaders.cmd_loader import DootCommandLoader
from doot.loaders.plugin_loader import DootPluginLoader
from doot.loaders.task_loader import DootTaskLoader
from doot.parsers.parser import DootArgParser

plugin_loader_key  : Final = doot.constants.DEFAULT_PLUGIN_LOADER_KEY
command_loader_key : Final = doot.constants.DEFAULT_COMMAND_LOADER_KEY
task_loader_key    : Final = doot.constants.DEFAULT_TASK_LOADER_KEY

preferred_cmd_loader  = doot.config.on_fail("default").loaders.command()
preferred_task_loader = doot.config.on_fail("default").loaders.task()
preferred_parser      = doot.config.on_fail("default").loaders.parser()

defaulted_file = doot.config.on_fail(pl.Path(".doot_defaults.toml"), pl.Path).report.defaulted_file(pl.Path)

@doot.check_protocol
class DootOverlord(Overlord_p):
    """
    Main control point for doot.
    prefers passed in loaders, then plugins it finds.

    default cmds are provided by the cmd loader
    """
    _help = ["An opinionated rewrite of Doit"]

    @staticmethod
    def print_version():
        """ print doot version (includes path location) """
        print("Doot Version: %s", doot.__version__)
        print("lib @", os.path.dirname(os.path.abspath(__file__)))

    def __init__(self, *, loaders:dict[str, Loader_i]=None, config_filenames:tuple=('doot.toml', 'pyproject.toml'), extra_config:dict|Tomler=None, args:list=None, log_config:None|DootLogConfig=None):
        logging.debug("Initialising Overlord")
        self.args           = args or sys.argv[:]
        self.BIN_NAME       = self.args[0].split('/')[-1]
        self.loaders        = loaders or dict()
        self.log_config     = log_config

        self.plugins     : None|Tomler = None
        self.cmds        : None|Tomler = None
        self.taskers     : None|Tomler = None
        self.current_cmd : Command_i      = None
        self.taskers     : list[Tasker_i] = []

        self._load_plugins(extra_config)
        self._load_commands(extra_config)
        self._load_taskers(extra_config)
        self._parse_args()
        logging.debug("Core Overlord Initialisation complete")

    @property
    def param_specs(self) -> list[DootParamSpec]:
        return [
           self.make_param(name="version" , prefix="--"),
           self.make_param(name="help"    , prefix="--"),
           self.make_param(name="verbose" , prefix="--"),
           self.make_param(name="debug",    prefix="--")
        ]

    @property
    def help(self) -> str:
        help_lines = ["", f"Doot v{doot.__version__}", ""]
        help_lines += self._help

        params = self.param_specs
        if bool(params):
            help_lines += ["", "Params:"]
            help_lines += sorted(str(x) for x in self.param_specs)

        help_lines.append("")
        help_lines.append("Commands: ")
        help_lines += sorted(x.helpline for x in self.cmds.values())

        return "\n".join(help_lines)

    def _load_plugins(self, extra_config:dict|Tomler=None):
        """ Use a plugin loader to find all applicable `importlib.EntryPoint`s  """
        self.plugin_loader    = self.loaders.get(plugin_loader_key, DootPluginLoader())
        self.plugin_loader.setup(extra_config)
        self.plugins : Tomler = self.plugin_loader.load()

    def _load_commands(self, extra_config):
        """ Select Commands from the discovered plugins """
        match (self.loaders.get(command_loader_key, None) or self.plugins.on_fail([], list).command_loader()):
            case []:
                self.cmd_loader = DootCommandLoader()
            case CommandLoader_p() as l:
                self.cmd_loader = l
            case [EntryPoint() as l]:
                self.cmd_loader = l.load()()
            case [EntryPoint() as l, *_] if preferred_cmd_loader == "default":
                self.cmd_loader = l.load()()
            case [*_] as loaders:
                matching_loaders = [x for x in loaders if x.name == preferred_cmd_loader]
                if not bool(matching_loaders):
                    raise KeyError("No Matching Command Loader found: ", preferred_cmd_loader, loaders)
                loaded = matching_loaders[0].load()
                self.cmd_loader = loaded()

        if self.cmd_loader is None:
            raise TypeError("Command Loader is not initialised")
        if not isinstance(self.cmd_loader, CommandLoader_p):
            raise TypeError("Attempted to use a non-CommandLoader_p as a CommandLoader: ", self.cmd_loader)

        self.cmd_loader.setup(self.plugins, extra_config)
        self.cmds = self.cmd_loader.load()

    def _load_taskers(self, extra_config):
        """ Load task entry points """
        match (self.loaders.get(task_loader_key, None) or self.plugins.on_fail([], list).task_loader()):
            case []:
                self.task_loader = DootTaskLoader()
            case TaskLoader_p() as l:
                self.task_loader = l
            case [EntryPoint() as l]:
                self.task_loader = l.load()()
            case [EntryPoint() as l, *_] if preferred_task_loader == "default":
                self.task_loader = l.load()()
            case [*_] as loaders:
                matching_loaders = [x for x in loaders if x.name == preferred_task_loader]
                if not bool(matching_loaders):
                    raise KeyError("No Matching Task Loader found: ", preferred_task_loader, loaders)
                loaded = matching_loaders[0].load()
                self.task_loader = loaded()

        if self.task_loader is None:
            raise TypeError("Task Loader is not initialised")
        if not isinstance(self.task_loader, TaskLoader_p):
            raise TypeError("Attempted to use a non-Commandloader_i as a CommandLoader: ", self.cmd_loader)

        self.task_loader.setup(self.plugins, extra_config)
        self.taskers = self.task_loader.load()

    def _parse_args(self, args=None):
        """ use the found task and command arguments to make sense of sys.argv """
        match (self.loaders.get("parser", None) or self.plugins.on_fail([], list).parser()):
            case []:
                self.parser = DootArgParser()
            case ArgParser_i() as l:
                self.parser = l
            case [EntryPoint() as l]:
                self.parser = l.load()()
            case [EntryPoint() as l, *_] if preferred_parser == "default":
                self.parser = l.load()()
            case [*_] as parsers:
                matching_parsers = [x for x in parsers if x.name == preferred_parser]
                if not bool(matching_parsers):
                    raise KeyError("No Matching parser found: ", preferred_parser, parsers)
                loaded = matching_loaders[0].load()
                self.parser = loaded()

        if not isinstance(self.parser, ArgParser_i):
            raise TypeError("Improper argparser specified: ", self.arg_parser)

        doot.args = self.parser.parse(args or self.args, doot_specs=self.param_specs, cmds=self.cmds, tasks=self.taskers)

    def _cli_arg_response(self) -> bool:
        """ Overlord specific cli arg responses. modify verbosity,
          print version, and help.
        """
        if doot.args.head.args.verbose and self.log_config:
            printer.info("Switching to Verbose Output")
            self.log_config.set_level("NOTSET")
            pass

        logging.info("CLI Args: %s", doot.args._table())
        logging.info("Plugins: %s", dict(self.plugins))
        logging.info("Taskers: %s", self.taskers.keys())

        if doot.args.head.args.version:
            printer.info("\n\n----- Doot Version: %s\n\n", doot.__version__)
            return True

        if doot.args.head.args.help:
            printer.info(self.help)

            return True

        return False

    def __call__(self, cmd=None):

        if not doot.args.on_fail((None,)).cmd.args.suppress_header():
            printer.info("----------------------------------------------")
            printer.info("-------------------- Doot --------------------")
            printer.info("----------------------------------------------")

        if doot.args.head.args.debug:
            breakpoint()
            pass

        # perform head args
        if self._cli_arg_response():
            return

        # do the command
        target = (cmd
            or doot.args.on_fail(None).cmd.name()
            or doot.constants.DEFAULT_CLI_CMD)

        logging.info("Overlord Calling: %s", cmd or doot.args.cmd.name)
        self.current_cmd = self.cmds.get(target, None)
        if self.current_cmd is None:
            logging.error("Specified Command Couldn't be Found: %s", target)
            return

        self.current_cmd(self.taskers, self.plugins)

    def shutdown(self):
        """ Doot has finished normally, so report on what was done """
        logging.info("Shutting Doot Down Normally, reporting defaulted tomler values")
        # defaulted_locs = doot.DootLocData.report_defaulted()
        defaulted_toml = tomler.Tomler.report_defaulted()

        with open(defaulted_file, 'w') as f:
            f.write("# default values used:\n")
            f.write("\n".join(defaulted_toml) + "\n\n")
            # f.write("[.directories]\n")
            # f.write("\n".join(defaulted_locs))
