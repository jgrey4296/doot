#!/usr/bin/env python3
"""
Doot : An Opinionated refactor of the Doit Task Runner.

"""
# Imports:
from __future__ import annotations

import sys
import logging as logmod
import typing
from ._interface import __version__
from .control.overlord import OverlordFacade

import __main__

if typing.TYPE_CHECKING:
    from typing import Callable
    from jgdv.structs.chainguard import ChainGuard
    from jgdv.structs.locator._interface import Locator_p
    from jgdv.logging._interface import LogConfig_p
    from doot.reporters._interface import Reporter_p

    aliases         : ChainGuard
    args            : ChainGuard
    config          : ChainGuard
    constants       : ChainGuard
    loaded_cmds     : ChainGuard
    loaded_plugins  : ChainGuard
    loaded_tasks    : ChainGuard
    locs            : Locator_p
    log_config      : LogConfig_p
    report          : Reporter_p
    cmd_aliases     : ChainGuard
    ##--| methods
    load            : Callable
    load_reporter   : Callable
    update_aliases  : Callable


##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


match getattr(__main__, "doot_setup", False):
    # Initialises the overlord as the 'doot' module
    case False:
        sys.modules[__name__].__class__ = OverlordFacade
        # Initialise the module manually
        OverlordFacade.__init__(sys.modules[__name__], __name__) # type: ignore[arg-type]
        __main__.doot_setup = True
    case True:
        # Nothing to do
        pass
