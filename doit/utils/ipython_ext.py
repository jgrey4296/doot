#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


def load_ipython_extension(ip=None):  # pragma: no cover
    """
    Defines a ``%doit`` magic function[1] that discovers and execute tasks
    from IPython's interactive variables (global namespace).

    It will fail if not invoked from within an interactive IPython shell.

    .. Tip::
        To permanently add this magic-function to your IPython, create a new
        script inside your startup-profile
        (``~/.ipython/profile_default/startup/doit_magic.ipy``) with the
        following content:

            %load_ext doit
            %reload_ext doit
            %doit list

    [1] http://ipython.org/ipython-doc/dev/interactive/tutorial.html#magic-functions
    """
    from IPython.core.getipython import get_ipython
    from IPython.core.magic import register_line_magic

    from doit.cmd_base import ModuleTaskLoader
    from doit.doit_cmd import DoitMain

    # Only (re)load_ext provides the ip context.
    ip = ip or get_ipython()

    @register_line_magic
    def doit(line):
        """
        Run *doit* with `task_creators` from all interactive variables
        (IPython's global namespace).

        Examples:

            >>> %doit --help          ## Show help for options and arguments.

            >>> def task_foo():
                    return {'actions': ['echo hi IPython'],
                            'verbosity': 2}

            >>> %doit list            ## List any tasks discovered.
            foo

            >>> %doit                 ## Run any tasks.
            .  foo
            hi IPython

        """
        # Override db-files location inside ipython-profile dir,
        # which is certainly writable.
        prof_dir = ip.profile_dir.location
        opt_vals = {'dep_file': os.path.join(prof_dir, 'db', '.doit.db')}
        commander = DoitMain(ModuleTaskLoader(ip.user_module),
                             extra_config={'GLOBAL': opt_vals})
        commander.BIN_NAME = 'doit'
        commander.run(line.split())

# also expose another way of registering ipython extension
register_doit_as_IPython_magic = load_ipython_extension
