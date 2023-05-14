
#!/usr/bin/env python3
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
import importlib
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
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

from collections import defaultdict
from importlib.metadata import entry_points, EntryPoint
import tomler
import doot
import doot.constants
from doot._abstract.loader import PluginLoader_i

TASK_STRING = "task_"

##-- loader cli params
#### options related to dooter.py
# select dodo file containing tasks
opt_doot = {
    "section" : "task loader",
    "name"    : "dooter",
    "short"   : "f",
    "long"    : "file",
    "type"    : str,
    "default" : str(doot.default_dooter),
    "env_var" : "DOOT_FILE",
    "help"    : "load task from doot FILE [default: %(default)s]"
}

opt_break = {
    "section" : "task loader",
    "name"    : "break",
    "short"   : "b",
    "long"    : "break",
    "type"    : bool,
    "default" : False,
    "help"    : "Start a debugger before loading tasks, to set breakpoints"
    }

# cwd
opt_cwd = {
    'section': 'task loader',
    'name': 'cwdPath',
    'short': 'd',
    'long': 'dir',
    'type': str,
    'default': None,
    'help': ("set path to be used as cwd directory "
             "(file paths on dodo file are relative to dodo.py location).")
}

# seek dodo file on parent folders
opt_seek_file = {
    'section': 'task loader',
    'name': 'seek_file',
    'short': 'k',
    'long': 'seek-file',
    'type': bool,
    'default': False,
    'env_var': 'DOIT_SEEK_FILE',
    'help': ("seek dodo file on parent folders [default: %(default)s]")
}

##-- end loader cli params

class DootPluginLoader(PluginLoader_i):

    def setup(self, extra_config=None):
        self.plugins = defaultdict(list)
        match extra_config:
            case None:
                self.extra_config = {}
            case dict():
                self.extra_config = tomler.Tomler(table=extra_config)
            case tomler.Tomler():
                self.extra_config = extra_config

    def load(self) -> dict:
        """
        use entry_points(group="doot")
        add to the config tomler
        """
        logging.debug("Loading Entry Points: %s", doot.constants.PLUGIN_TOML_PREFIX)
        try:
            env_eps      = config.on_fail({}).plugins(wrapper=dict)
            extra_eps    = self.extra_config.on_fail({}).plugins(wrapper=dict)
            plugin_types = set(doot.constants.FRONTEND_PLUGIN_TYPES + doot.constants.BACKEND_PLUGIN_TYPES)

            if doot.config.on_fail(False).skip_plugin_search():
                pass
            else:
                logging.info("Searching environment for plugins, skip with `skip_plugin_search` in config")
                for plugin_type in plugin_types:
                    plugin_group = "{}.{}".format(doot.constants.PLUGIN_TOML_PREFIX, plugin_type)
                    # Load env wide entry points
                    for entry_point in entry_points(group=plugin_group):
                        self.plugins[plugin_type].append(entry_point)

            # load config entry points
            for k, v in env_eps.items():
                if k not in plugin_types:
                    logging.warning("Unknown plugin type found in config: %s", k)
                    continue
                ep = EntryPoint(name=v, value=v, group=k)
                self.plugins[k].append(ep)

            # load extra-config entry points
            for k,v in extra_eps.items():
                if k not in plugin_types:
                    logging.warning("Unknown plugin type found in extra config: %s", k)
                    continue
                ep = EntryPoint(name=v, value=v, group=k)
                self.plugins[k] = EntryPoint(name=k, value=v, group=doot.constants.PLUGIN_TOML_PREFIX)

            self.append_defaults()
            logging.debug("Found {len(self.plugins)} plugins")
            return self.plugins
        except Exception as err:
            logging.error("Plugin Failed to Load:")


    def append_defaults(self):
        if doot.config.on_fail(False).skip_default_plugins():
            logging.info("Skipping Default Plugins")
            return

        make_ep = lambda x, y, z: EntryPoint(name=x, value=y, group=z)

        self.plugins["command_loader"].append(make_ep(doot.constants.DEFAULT_COMMAND_LOADER_KEY, "doot.loaders.cmd_loader:DootCommandLoader", "command_loader"))
        self.plugins["task_loader"].append(make_ep(doot.constants.DEFAULT_TASK_LOADER_KEY, "doot.loaders.task_loader:DootTaskLoader", "task_loader"))

        self.plugins['command']  += []
        self.plugins['reporter'] += []
        self.plugins['database'] += []
        self.plugins['control']  += []
        self.plugins['dispatch'] += []
        self.plugins['runner']   += []
        self.plugins['parser']   += []
        self.plugins['action']   += []
        self.plugins['tasker']   += []
        self.plugins['task']     += []
        self.plugins['group']    += []
