#!/usr/bin/env python3
"""
Alternative doot cli runner, to use the doot loader
"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib
import pathlib as pl
import sys
from bdb import BdbQuit
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from importlib.resources import files
from re import Pattern
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
import sh
import stackprinter
import tomlguard as TG

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.utils.log_config import DootLogConfig

# ##-- end 1st party imports

##-- logging
logging         = logmod.root
printer         = logmod.getLogger("doot._printer")
shutdown_l      = printer.getChild("shutdown")
fail_l          = printer.getChild("fail")
##-- end logging

template_path      = files("doot.__templates")

def main():
    result  = 1
    overlord = None
    try:
        log_config = DootLogConfig()
        # --- Setup
        if not bool(doot.config):
            doot.setup()

        log_config.setup()

        logging.info("Doot Calling Args: %s", sys.argv)
        # ##-- 1st party imports
        from doot.control.overlord import DootOverlord
        from doot.loaders.plugin_loader import DootPluginLoader

        # ##-- end 1st party imports
        overlord  = DootOverlord(loaders={"plugin": DootPluginLoader().setup(sys.argv[:]) },
                                 config_filenames=[doot.constants.paths.DEFAULT_LOAD_TARGETS],
                                 log_config=log_config,
                                 args=sys.argv[:])

        # --- Do whatever thats been triggered
        result    = overlord()

    ##-- handle doot errors
    except (doot.errors.DootEarlyExit, BdbQuit):
        shutdown.warning("Early Exit Triggered")
        result = 0
    except doot.errors.DootMissingConfigError as err:
        result = 0
        # Handle missing files
        if pl.Path(doot.constants.on_fail(["doesntexist"]).paths.DEFAULT_LOAD_TARGETS()[0]).exists():
            pass
        elif input("No toml config data found, create stub doot.toml? _/n ") != "n":
            template = template_path.joinpath(doot.constants.paths.TOML_TEMPLATE)
            target = pl.Path(doot.constants.on_fail(["doot.toml"]).paths.DEFAULT_LOAD_TARGETS()[0])
            target.write_text(template.read_text())
            shutdown.info("Doot Config File Stubbed: %s", target)
    except doot.errors.DootTaskError as err:
        fail_prefix = doot.constants.printer.fail_prefix
        fail_l.error("%s %s : %s", fail_prefix, err.general_msg, err.task_name)
        fail_l.error("%s Source: %s", fail_prefix, err.task_source)
        fail_l.error("%s %s", fail_prefix, str(err))
    except doot.errors.DootError as err:
        fail_prefix = doot.constants.printer.fail_prefix
        fail_l.error("%s", err.general_msg)
        fail_l.error("---- %s", str(err))
    ##-- end handle doot errors
    ##-- handle todo errors
    except NotImplementedError as err:
        logging.error(stackprinter.format())
        fail_l.error("Not Implemented: %s", err)
    ##-- end handle todo errors
    ##-- handle general errors
    except Exception as err:
        logging.error(stackprinter.format())
        fail_l.error("Python Error: %s", err)
    ##-- end handle general errors
    finally: # --- final shutdown
        if overlord:
            overlord.shutdown()

        sys.exit(result)

##-- ifmain
if __name__ == '__main__':
    main()
##-- end ifmain
