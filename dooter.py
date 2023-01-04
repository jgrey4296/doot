# -*- mode:doit; -*-
"""
Stub dooter file for task authoring

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
DOIT_CONFIG = {
    "action_string_formatting" : "new"
}

##-- end config

##-- post-config doot imports
from doot.groups import *
from doot.groups_secondary import *
##-- end post-config doot imports


if __name__ == "dooter":
    # the equivalent of main
    pass
