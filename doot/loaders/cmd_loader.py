#!/usr/bin/env python3
"""

"""
# Imports:
##-- imports
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
# import abc
# import datetime
# import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from importlib.metadata import entry_points
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
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
from doot._abstract import Command_i, CommandLoader_p

# ##-- end 1st party imports

# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@doot.check_protocol
class DootCommandLoader(CommandLoader_p):
    """
      Default Command loaded. using the loaded plugins,
      selects "command", calls load on each entry point, and if the obj returned is a subclass of Command_i,
      instantiates it
    """

    def setup(self, plugins, extra:Maybe[list|dict|ChainGuard]=None) -> Self:
        self.cmd_plugins : list[EntryPoint] = plugins.get("command", [])
        self.cmds = {}

        match extra:
            case None:
                self.extra = []
            case list():
                self.extra = extra
            case dict():
                self.extra = ChainGuard(extra).on_fail([]).tasks()
            case ChainGuard():
                self.extra = extra.on_fail([]).tasks()

        return self

    def load(self) -> ChainGuard[Command_i]:
        logging.debug("---- Loading Commands")
        for cmd_point in self.cmd_plugins:
            try:
                logging.debug("Loading Cmd: %s", cmd_point.name)
                # load the plugins
                cmd = cmd_point.load()
                if not issubclass(cmd, Command_i):
                    raise TypeError("Not a Command_i", cmd)

                self.cmds[cmd_point.name] = cmd()
                self.cmds[cmd_point.name]._name = cmd_point.name
            except Exception as err:
                raise doot.errors.PluginLoadError("Attempted to load a non-command: %s : %s", cmd_point, err) from err

        return ChainGuard(self.cmds)
