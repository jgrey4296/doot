#!/usr/bin/env python3
"""
Alternative doot cli runner, to use the doot loader
"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib
import pathlib as pl
import sys
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref
##-- end imports

logging         = logmod.root
printer         = logmod.getLogger("doot._printer")

from importlib.resources import files
import sh
import stackprinter
import tomlguard as TG
import doot
from bdb import BdbQuit
from doot.utils.log_config import DootLogConfig

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

        logging.info("Called with: %s", sys.argv)
        from doot.loaders.plugin_loader import DootPluginLoader
        from doot.control.overlord import DootOverlord
        overlord  = DootOverlord(loaders={"plugin": DootPluginLoader().setup(sys.argv[:]) },
                                 config_filenames=[doot.constants.paths.DEFAULT_LOAD_TARGETS],
                                 log_config=log_config,
                                 args=sys.argv[:])

        # --- Do whatever thats been triggered
        result    = overlord()

    ##-- handle doot errors
    except (doot.errors.DootEarlyExit, BdbQuit):
        printer.warning("Early Exit Triggered")
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
            logging.info("Stubbed")
    except doot.errors.DootTaskError as err:
        printer.error("%s : %s", err.general_msg, err.task_name)
        printer.error("---- Source: %s", err.task_source)
        printer.error("---- %s", str(err))
    except doot.errors.DootError as err:
        printer.error("%s", err.general_msg)
        printer.error("---- %s", str(err))
    ##-- end handle doot errors
    ##-- handle todo errors
    except NotImplementedError as err:
        logging.error(stackprinter.format())
        printer.error("Not Implemented: %s", err)
    ##-- end handle todo errors
    ##-- handle general errors
    except Exception as err:
        logging.error(stackprinter.format())
        # logging.error("Python Error: %s", err)
    ##-- end handle general errors
    finally: # --- final shutdown
        if overlord:
            overlord.shutdown()

        sys.exit(result)

##-- ifmain
if __name__ == '__main__':
    main()
##-- end ifmain
