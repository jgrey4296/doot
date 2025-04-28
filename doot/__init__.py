#!/usr/bin/env python3
"""
Doot : An Opinionated refactor of the Doit Task Runner.

"""
# ruff: noqa: ANN001, PLW0603, FBT003
# Imports:
from __future__ import annotations

import sys
import logging as logmod
from ._interface import __version__
from .control.overlord import DootOverlord

import __main__

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

match getattr(__main__, "doot_setup", False):
    # Initialises the overlord as the 'doot' module
    case False:
        sys.modules[__name__].__class__ = DootOverlord
        sys.modules[__name__].__init__(__name__)
        setattr(__main__, "doot_setup", True)
    case True:
        pass
