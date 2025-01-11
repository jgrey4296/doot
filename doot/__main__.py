#!/usr/bin/env python3
"""
The doot cli runner
"""
# ruff: noqa: PLR0912, BLE001
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
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

# ##-- end 1st party imports

##-- logging
logging         = logmod.root
printer         = doot.subprinter()
shutdown_l      = doot.subprinter("shutdown")
fail_l          = doot.subprinter("fail")
##-- end logging

template_path      = files("doot.__templates")

def main() -> None:
    """ The Main Doot CLI Program.
    Loads data and plugins before starting the requested command.
    """
    result  = 1
    overlord = None
    try:
        # --- Setup
        if not bool(doot.config):
            doot.setup()
    except doot.errors.MissingConfigError:
        doot._null_setup()

    try:
        # ##-- 1st party imports
        from doot.control.overlord import DootOverlord
        from doot.loaders.plugin_loader import DootPluginLoader

        # ##-- end 1st party imports
        overlord  = DootOverlord(loaders={"plugin": DootPluginLoader().setup(sys.argv[:]) },
                                 config_filenames=[doot.constants.paths.DEFAULT_LOAD_TARGETS],
                                 log_config=doot.log_config,
                                 args=sys.argv[:])
        overlord.setup()
        # --- Do whatever thats been triggered
        result    = overlord()

    except (doot.errors.EarlyExit, doot.errors.Interrupt, BdbQuit):
        shutdown_l.warning("Early Exit Triggered")
        result = 0
    except doot.errors.MissingConfigError as err:
        result = 0
        base_target = pl.Path(doot.constants.on_fail(["doot.toml"]).paths.DEFAULT_LOAD_TARGETS()[0])
        # Handle missing files
        if base_target.exists():
            fail_l.error("Base Config Target exists but it contains no valid config: %s", base_target)
        else:
            fail_l.warning("No toml config data found, create a doot.toml by calling `doot stub --config`")
    except doot.errors.ConfigError as err:
        fail_l.warning(err)
    except doot.errors.TaskError as err:
        fail_prefix = doot.constants.printer.fail_prefix
        fail_l.error("%s %s : %s", err, exc_info=err)
        fail_l.error("%s Source: %s", fail_prefix, err.task_source)
    except doot.errors.BackendError as err:
        fail_prefix = doot.constants.printer.fail_prefix
        fail_l.error("%s %s", fail_prefix, err, exc_info=err)
    except doot.errors.FrontendError as err:
        fail_prefix = doot.constants.printer.fail_prefix
        fail_l.error("%s %s : %s", fail_prefix, err, err.__cause__)
    except doot.errors.DootError as err:
        fail_prefix = doot.constants.printer.fail_prefix
        fail_l.error("%s %s", fail_prefix,  err, exc_info=err)
    except NotImplementedError as err:
        fail_l.error("Not Implemented: %s", err, exc_info=err)
    except Exception as err:
        pl.Path("doot.lasterror").write_text(stackprinter.format())
        fail_l.error("Python Error:", exc_info=err)
    finally:
        if overlord:
            overlord.shutdown()

        sys.exit(result)

##-- ifmain
if __name__ == '__main__':
    main()
##-- end ifmain
