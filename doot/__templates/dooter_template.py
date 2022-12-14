# -*- mode:doit; -*-
"""
Template dodo when using doot

"""
# https://pydoit.org/
##-- imports
import pathlib as pl
from doit.action import CmdAction
from doit import create_after
from doit.tools import set_trace, Interactive, PythonInteractiveAction
from doit.task import clean_targets

import doot
##-- end imports

##-- config
datatoml    = doot.setup_py()
check_build = doot.check_build

DOIT_CONFIG = {
    "default_tasks" : [],
    }

##-- end config

##-- post-config doot imports
from doot.files.clean import clean_cache_globs, py_cache_globs
from doot.files.listall import task_listall

from doot.groups import *
##-- end post-config doot imports

##-- actions
## Can have auto filled parameters of:
## targets, dependencies, changed
## and 'task' gives access to all metadata

##-- end actions

##-- tasks


##-- end tasks
