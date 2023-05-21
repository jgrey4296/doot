
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

skip_default_plugins = doot.config.on_fail(False).skip_default_plugins()
skip_plugin_search   = doot.config.on_fail(False).skip_plugin_search()
env_eps              = doot.config.on_fail({}).plugins(wrapper=dict)
plugin_types         = set(doot.constants.FRONTEND_PLUGIN_TYPES + doot.constants.BACKEND_PLUGIN_TYPES)

class DootPluginLoader(PluginLoader_i):

    def setup(self, extra_config=None):
        self.plugins = defaultdict(list)
        match extra_config:
            case None:
                self.extra_config = {}
            case dict():
                self.extra_config = tomler.Tomler(extra_config)
            case tomler.Tomler():
                self.extra_config = extra_config

    def load(self, arg) -> dict[str, list]:
        """
        use entry_points(group="doot")
        add to the config tomler
        """
        logging.debug("Loading Entry Points: %s", doot.constants.PLUGIN_TOML_PREFIX)
        extra_eps    = self.extra_config.on_fail({}).plugins(wrapper=dict)
        if skip_plugin_search:
            pass
        else:
            logging.info("Searching environment for plugins, skip with `skip_plugin_search` in config")
            for plugin_type in plugin_types:
                try:
                    plugin_group = "{}.{}".format(doot.constants.PLUGIN_TOML_PREFIX, plugin_type)
                    # Load env wide entry points
                    for entry_point in entry_points(group=plugin_group):
                        self.plugins[plugin_type].append(entry_point)
                except Exception as err:
                    raise ResourceWarning(f"Plugin Failed to Load: {plugin_group} : {entry_point}") from err


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

        try:
            self.append_defaults()
        except Exception as err:
            raise ResourceWarning("Failed to load plugin defaults") from err
        logging.debug("Found {len(self.plugins)} plugins")
        return self.plugins


    def append_defaults(self):
        if skip_default_plugins:
            logging.info("Skipping Default Plugins")
            return

        make_ep = lambda x, y, z: EntryPoint(name=x, value=y, group=z)

        self.plugins["command_loader"].append(make_ep(doot.constants.DEFAULT_COMMAND_LOADER_KEY, "doot.loaders.cmd_loader:DootCommandLoader", "command_loader"))
        self.plugins["task_loader"].append(make_ep(doot.constants.DEFAULT_TASK_LOADER_KEY, "doot.loaders.task_loader:DootTaskLoader", "task_loader"))

        self.plugins['command']  += []
        self.plugins['reporter'] += []
        self.plugins['database'] += []
        self.plugins['tracker']  += []
        self.plugins['runner']   += []
        self.plugins['parser']   += []
        self.plugins['action']   += []
        # self.plugins['tasker'] += []
        self.plugins['task']     += []
        # self.plugins['group']  += []
