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
from importlib.metadata import entry_points
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

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

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from doot._abstract import Command_p, CommandLoader_p
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@Proto(CommandLoader_p)
class DootCommandLoader:
    """
      Default Command loaded. using the loaded plugins,
      selects "command", calls load on each entry point, and if the obj returned is a subclass of Command_p,
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

    def load(self) -> ChainGuard[Command_p]:
        logging.debug("---- Loading Commands")
        for cmd_point in self.cmd_plugins:
            try:
                logging.debug("Loading Cmd: %s", cmd_point.name)
                # load the plugins
                cmd = cmd_point.load()
                if not issubclass(cmd, Command_p):
                    raise TypeError("Not a Command_p", cmd)

                self.cmds[cmd_point.name] = cmd()
                self.cmds[cmd_point.name]._name = cmd_point.name
            except Exception as err:
                raise doot.errors.PluginLoadError("Attempted to load a non-command: %s : %s", cmd_point, err) from err

        return ChainGuard(self.cmds)
