#!/usr/bin/env python3
"""
Doot : An Opinionated refactor of the Doit Task Runner.

"""
# ruff: noqa: ANN001, PLW0603, FBT003
# Imports:
from __future__ import annotations

import logging as logmod
from ._interface import __version__
from .control.overlord import DootOverlord

import __main__

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

match getattr(__main__, "doot_setup", False):
    case False:
        _overlord = DootOverlord()
        setattr(__main__, "doot_setup", True)
    case True:
        pass

def __getattr__(name):
    """ Use the DootOverlord object for the main global vars and setup """
    return getattr(_overlord, name)
