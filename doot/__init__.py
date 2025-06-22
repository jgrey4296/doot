#!/usr/bin/env python3
"""
Doot : An Opinionated refactor of the Doit Task Runner.

"""
# ruff: noqa: ANN001, PLW0603, FBT003
# Imports:
from __future__ import annotations

import sys
import logging as logmod
import typing
from ._interface import __version__
from .control.overlord import OverlordFacade

import __main__

if typing.TYPE_CHECKING:
    from jgdv.structs.chainguard._interface import ChainGuard_p
    from jgdv.structs.locator._interface import Locator_p
    from jgdv.logging._interface import LogConfig_p

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

config       : ChainGuard_p
constants    : ChainGuard_p
aliases      : ChainGuard_p
log_config   : LogConfig_p
args         : ChainGuard_p
locs         : Locator_p

match getattr(__main__, "doot_setup", False):
    # Initialises the overlord as the 'doot' module
    case False:
        sys.modules[__name__].__class__ = OverlordFacade
        # Initialise the module manually
        sys.modules[__name__].__init__(__name__) # type: ignore
        __main__.doot_setup = True
    case True:
        # Nothing to do
        pass
