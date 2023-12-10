
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
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

from collections import defaultdict
from importlib.metadata import entry_points, EntryPoint
import tomlguard
import doot
import doot.constants
from doot._abstract import PluginLoader_p

skip_default_plugins        = doot.config.on_fail(False).skip_default_plugins()
skip_plugin_search          = doot.config.on_fail(False).skip_plugin_search()
env_plugins                 = doot.config.on_fail({}).plugins(wrapper=dict)
plugin_types                = set(doot.constants.FRONTEND_PLUGIN_TYPES + doot.constants.BACKEND_PLUGIN_TYPES)
cmd_loader_key  : Final     = doot.constants.DEFAULT_COMMAND_LOADER_KEY
task_loader_key : Final     = doot.constants.DEFAULT_TASK_LOADER_KEY

def make_ep (x, y, z):
    if z not in plugin_types:
        raise doot.errors.DootPluginError("Plugin Type Not Found: %s : %s", z, (x, y))
    return EntryPoint(name=x, value=y, group="{}.{}".format(doot.constants.PLUGIN_TOML_PREFIX, z))


@doot.check_protocol
class DootPluginLoader(PluginLoader_p):
    """
    Load doot plugins from the system, to choose from with doot.toml or cli args
    """

    def setup(self, extra_config=None) -> Self:
        self.plugins = defaultdict(list)
        match extra_config:
            case None:
                self.extra_config = tomlguard.TomlGuard({})
            case dict():
                self.extra_config = tomlguard.TomlGuard(extra_config)
            case tomlguard.TomlGuard():
                self.extra_config = extra_config

        return self

    def load(self) -> TomlGuard[EntryPoint]:
        """
        use entry_points(group="doot")
        add to the config tomlguard
        """
        logging.debug("---- Loading Plugins: %s", doot.constants.PLUGIN_TOML_PREFIX)
        try:
            self._load_system_plugins()
        except Exception as err:
            raise doot.errors.DootPluginError("Failed to load system wide plugins: %s", err) from err

        try:
            self._load_from_toml()
        except Exception as err:
            raise doot.errors.DootPluginError("Failed to load toml specified plugins: %s", err) from err

        try:
            self._load_extra_plugins()
        except Exception as err:
            raise doot.errors.DootPluginError("Failed to load command line/dooter specified plugins: %s", err) from err

        try:
            self._append_defaults()
        except Exception as err:
            raise doot.errors.DootPluginError("Failed to load plugin defaults: %s", err) from err

        logging.debug("Found %s plugins", len(self.plugins))
        PluginLoader_p.loaded = tomlguard.TomlGuard(self.plugins)
        return PluginLoader_p.loaded

    def _load_system_plugins(self):
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
                    raise doot.errors.DootPluginError("Plugin Failed to Load: %s : %s : %s", plugin_group, entry_point, err) from err

    def _load_from_toml(self):
        # load config entry points
        for cmd_group, vals in env_plugins.items():
            if cmd_group not in plugin_types:
                logging.warning("Unknown plugin type found in config: %s", cmd_group)
                continue
            if not isinstance(vals, (tomlguard.TomlGuard, dict)):
                logging.warning("Toml specified plugins need to be a dict of (cmdName : class): %s ", cmd_group)
                continue

            for name, cls in vals.items():
                ep = EntryPoint(name=name, value=cls, group=cmd_group)
                self.plugins[cmd_group].append(ep)

    def _load_extra_plugins(self):
        extra_eps    = self.extra_config.on_fail({}).plugins(wrapper=dict)
        # load extra-config entry points
        for k,v in extra_eps.items():
            if k not in plugin_types:
                logging.warning("Unknown plugin type found in extra config: %s", k)
                continue
            ep = EntryPoint(name=k, value=v, group=doot.constants.PLUGIN_TOML_PREFIX)
            logging.debug("Adding Plugin: %s", ep)
            self.plugins[k].append(ep)

    def _append_defaults(self):
        if skip_default_plugins:
            logging.info("Skipping Default Plugins")
            return

        self.plugins[cmd_loader_key].append(make_ep(cmd_loader_key, "doot.loaders.cmd_loader:DootCommandLoader", cmd_loader_key))
        self.plugins[task_loader_key].append(make_ep(task_loader_key, "doot.loaders.task_loader:DootTaskLoader", task_loader_key))

        for group, vals in doot.constants.DEFAULT_PLUGINS.items():
            self.plugins[group]  += [make_ep(x, y, group) for x,y in vals]
