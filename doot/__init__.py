#!/usr/bin/env python3
"""
Doot : An Opinionated refactor of the Doit Task Runner.

"""
# ruff: noqa: ANN001, PLW0603, FBT003
# Imports:
from __future__ import annotations

from ._interface import __version__

from .control.overlord import DootOverlord

_overlord                = DootOverlord()

def __getattr__(name):
    """ Use the DootOverlord object for the main global vars and setup """
    return getattr(_overlord, name)
