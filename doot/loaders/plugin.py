
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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from . import _interface as API  # noqa: N812
# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

from doot._abstract import PluginLoader_p
if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def build_entry_point (x:str, y:str, z:str) -> EntryPoint:
    """ Make an EntryPoint """
    if z not in API.plugin_types:
        raise doot.errors.PluginError("Plugin Type Not Found: %s : %s", z, (x, y))
    group = f"{API.PLUGIN_PREFIX}.{z}"
    return EntryPoint(name=x, value=y, group=group)

@Proto(PluginLoader_p)
class DootPluginLoader:
    """
    Load doot plugins from the system, to choose from with doot.toml or cli args
    TODO singleton?
    """

    def setup(self, extra_config:Maybe[dict|ChainGuard]=None) -> Self:
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
        loaded = ChainGuard(self.plugins)
        return loaded

    def _load_system_plugins(self) -> None:
        if API.skip_plugin_search:
            return

        logging.info("-- Searching environment for plugins, skip with `skip_plugin_search` in config")
        for plugin_type in API.plugin_types:
            try:
                plugin_group = f"{API.PLUGIN_PREFIX}.{plugin_type}"
                # Load env wide entry points
                for entry_point in entry_points(group=plugin_group):
                    self.plugins[plugin_type].append(entry_point)
            except Exception as err:
                raise doot.errors.PluginError("Plugin Failed to Load: %s : %s : %s", plugin_group, entry_point, err) from err

    def _load_from_toml(self) -> None:
        logging.info("-- Loading Plugins from Toml")
        # load config entry points
        for cmd_group, vals in API.env_plugins.items():
            if cmd_group not in API.plugin_types:
                logging.warning("Unknown plugin type found in config: %s", cmd_group)
                continue

            if not isinstance(vals, ChainGuard|dict):
                logging.warning("Toml specified plugins need to be a dict of (cmdName : class): %s ", cmd_group)
                continue

            for name, cls in vals.items():
                logging.debug("Creating Plugin Entry Point: %s : %s", cmd_group, name)
                ep = build_entry_point(name, cls, cmd_group)
                self.plugins[cmd_group].append(ep)

    def _load_extra_plugins(self) -> None:
        extra_eps    = self.extra_config.on_fail({}).plugins(wrapper=dict)
        if not bool(extra_eps):
            return

        logging.info("-- Loading Extra Plugins")
        # load extra-config entry points
        for k,v in extra_eps.items():
            if k not in API.plugin_types:
                logging.warning("Unknown plugin type found in extra config: %s", k)
                continue
            ep = build_entry_point(k, v, doot.constants.entrypoints.PLUGIN_TOML_PREFIX)
            logging.debug("Adding Plugin: %s", ep)
            self.plugins[k].append(ep)

    def _append_defaults(self) -> None:
        if API.skip_default_plugins:
            return

        logging.info("-- Loading Default Plugin Aliases")
        self.plugins[API.cmd_loader_key].append(build_entry_point(API.cmd_loader_key, API.DEFAULT_CMD_LOADER, API.cmd_loader_key))
        self.plugins[API.task_loader_key].append(build_entry_point(API.task_loader_key, API.DEFAULT_TASK_LOADER, API.task_loader_key))

        for group, vals in doot.aliases.items():
            logging.debug("Loading aliases: %s (%s)", group, len(vals))
            defined = {x.name for x in self.plugins[group]}
            defaults = {x : build_entry_point(x, y, group) for x,y in vals.items() if x not in defined}
            self.plugins[group]  += defaults.values()
