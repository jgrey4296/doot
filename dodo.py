# -*- mode:doit; -*-
"""
Template dodo when using doot
# https://pydoit.org/
"""
##-- imports
from __future__ import annotations
import pathlib as pl
from doit.action import CmdAction
from doit import create_after
from doit.tools import set_trace, Interactive, PythonInteractiveAction, LongRunning
from doit.task import clean_targets

import doot
##-- end imports

##-- config
data_toml = doot.setup()

DOIT_CONFIG = {
    "default_tasks" : [],
    "action_string_formatting" : "new",
    }

##-- end config

##-- post-config doot imports
from doot.files.clean_cache import CleanCacheAction, py_cache_globs

from doot.groups import *
from doot.groups_secondary import *
##-- end post-config doot imports
