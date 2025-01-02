
#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from collections import defaultdict
from importlib.metadata import EntryPoint, entry_points
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Maybe
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract import PluginLoader_p

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

skip_default_plugins        = doot.config.on_fail(False).startup.skip_default_plugins()
skip_plugin_search          = doot.config.on_fail(False).startup.skip_plugin_search()
env_plugins                 = doot.config.on_fail({}).startup.plugins(wrapper=dict)
plugin_types                = set(doot.constants.entrypoints.FRONTEND_PLUGIN_TYPES + doot.constants.entrypoints.BACKEND_PLUGIN_TYPES)
cmd_loader_key  : Final     = doot.constants.entrypoints.DEFAULT_COMMAND_LOADER_KEY
task_loader_key : Final     = doot.constants.entrypoints.DEFAULT_TASK_LOADER_KEY

def build_entry_point (x:str, y:str, z:str) -> EntryPoint:
    """ Make an EntryPoint """
    if z not in plugin_types:
        raise doot.errors.PluginError("Plugin Type Not Found: %s : %s", z, (x, y))
    return EntryPoint(name=x, value=y, group="{}.{}".format(doot.constants.entrypoints.PLUGIN_TOML_PREFIX, z))

@doot.check_protocol
class DootPluginLoader(PluginLoader_p):
    """
    Load doot plugins from the system, to choose from with doot.toml or cli args
    """
    loaded : ClassVar[ChainGuard] = None

    @staticmethod
    def get_loaded(group:str, name:str) -> Maybe[str]:
        if DootPluginLoader.loaded is None:
            return None
        if group not in DootPluginLoader.loaded:
            return None
        matches = [x.value for x in DootPluginLoader.loaded[group] if x.name == name]
        if bool(matches):
            return matches[0]

        return None

    def setup(self, extra_config=None) -> Self:
        self.plugins = defaultdict(list)
        match extra_config:
            case None:
                self.extra_config = ChainGuard({})
            case dict():
                self.extra_config = ChainGuard(extra_config)
            case ChainGuard():
                self.extra_config = extra_config

        return self

    def load(self) -> ChainGuard[EntryPoint]:
        """
        use entry_points(group="doot")
        add to the config ChainGuard
        """
        logging.debug("---- Loading Plugins: %s", doot.constants.entrypoints.PLUGIN_TOML_PREFIX)
        try:
            self._load_system_plugins()
        except Exception as err:
            raise doot.errors.PluginError("Failed to load system wide plugins: %s", err) from err

        try:
            self._load_from_toml()
        except Exception as err:
            raise doot.errors.PluginError("Failed to load toml specified plugins: %s", err) from err

        try:
            self._load_extra_plugins()
        except Exception as err:
            raise doot.errors.PluginError("Failed to load command line/dooter specified plugins: %s", err) from err

        try:
            self._append_defaults()
        except Exception as err:
            raise doot.errors.PluginError("Failed to load plugin defaults: %s", err) from err

        logging.debug("Found %s plugins", len(self.plugins))
        DootPluginLoader.loaded = ChainGuard(self.plugins)
        return DootPluginLoader.loaded

    def _load_system_plugins(self):
        if skip_plugin_search:
            return

        logging.info("-- Searching environment for plugins, skip with `skip_plugin_search` in config")
        for plugin_type in plugin_types:
            try:
                plugin_group = "{}.{}".format(doot.constants.entrypoints.PLUGIN_TOML_PREFIX, plugin_type)
                # Load env wide entry points
                for entry_point in entry_points(group=plugin_group):
                    self.plugins[plugin_type].append(entry_point)
            except Exception as err:
                raise doot.errors.PluginError("Plugin Failed to Load: %s : %s : %s", plugin_group, entry_point, err) from err

    def _load_from_toml(self):
        logging.info("-- Loading Plugins from Toml")
        # load config entry points
        for cmd_group, vals in env_plugins.items():
            if cmd_group not in plugin_types:
                logging.warning("Unknown plugin type found in config: %s", cmd_group)
                continue

            if not isinstance(vals, (ChainGuard, dict)):
                logging.warning("Toml specified plugins need to be a dict of (cmdName : class): %s ", cmd_group)
                continue

            for name, cls in vals.items():
                logging.debug("Creating Plugin Entry Point: %s : %s", cmd_group, name)
                ep = build_entry_point(name, cls, cmd_group)
                self.plugins[cmd_group].append(ep)

    def _load_extra_plugins(self):
        extra_eps    = self.extra_config.on_fail({}).plugins(wrapper=dict)
        if not bool(extra_eps):
            return

        logging.info("-- Loading Extra Plugins")
        # load extra-config entry points
        for k,v in extra_eps.items():
            if k not in plugin_types:
                logging.warning("Unknown plugin type found in extra config: %s", k)
                continue
            ep = build_entry_point(k, v, doot.constants.entrypoints.PLUGIN_TOML_PREFIX)
            logging.debug("Adding Plugin: %s", ep)
            self.plugins[k].append(ep)

    def _append_defaults(self):
        if skip_default_plugins:
            return

        logging.info("-- Loading Default Plugin Aliases")
        self.plugins[cmd_loader_key].append(build_entry_point(cmd_loader_key, "doot.loaders.cmd_loader:DootCommandLoader", cmd_loader_key))
        self.plugins[task_loader_key].append(build_entry_point(task_loader_key, "doot.loaders.task_loader:DootTaskLoader", task_loader_key))

        for group, vals in doot.aliases.items():
            logging.debug("Loading aliases: %s (%s)", group, len(vals))
            defined = {x.name for x in self.plugins[group]}
            defaults = {x : build_entry_point(x, y, group) for x,y in vals.items() if x not in defined}
            self.plugins[group]  += defaults.values()
