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

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

logging         = logmod.root
printer         = logmod.getLogger("doot._printer")

import stackprinter
import tomler
import doot
from doot.utils.log_config import DootLogConfig

def main():
    result  = 1
    errored = False
    try:
        log_config = DootLogConfig()
        # --- Setup
        if doot.config is None:
            doot.setup()

        log_config.setup()

        logging.info("Called with: %s", sys.argv)
        from doot.loaders.plugin_loader import DootPluginLoader
        from doot.control.overlord import DootOverlord
        overlord  = DootOverlord(loaders={"plugin": DootPluginLoader().setup(sys.argv[:]) },
                                 config_filenames=[doot.constants.DEFAULT_LOAD_TARGETS],
                                 log_config=log_config,
                                 args=sys.argv[:])

        # --- Do whatever thats been triggered
        result    = overlord()
        overlord.shutdown()

    except FileNotFoundError: # --- Handle missing files
        if not doot.constants.DEFAULT_LOAD_TARGETS[0].exists():
            if input("No toml config data found, create stub doot.toml? _/n ") != "n":
                doot.constants.DEFAULT_LOAD_TARGETS[0].write_text(doot.constants.TOML_TEMPLATE.read_text())
                logging.info("Stubbed")
    except Exception as err: # --- Handle general errors
        errored = True
        logging.error(stackprinter.format())
        logging.error("Error: %s", err)
    finally: # --- final shutdown
        announce_exit : bool = doot.constants.ANNOUNCE_EXIT
        announce_voice : str = doot.constants.ANNOUNCE_VOICE
        if doot.config is not None:
            say_on_exit = doot.config.on_fail(announce_exit, bool|str).notify.say_on_exit()
            voice       = doot.config.on_fail(announce_voice, str).notify.voice()

        match errored, say_on_exit:
            case False, str() as say_text:
                cmd = sh.say("-v", voice, "-r", "50", say_text)
            case False, True:
                cmd = sh.say("-v", voice, "-r", "50", "Doot Has Finished")
            case True, True|str():
                cmd = sh.say("-v", voice, "-r", "50", "Doot Encountered a problem")
            case _:
                cmd = None
        if cmd is not None:
            cmd.execute()

        sys.exit(result)


##-- ifmain
if __name__ == '__main__':
    main()
##-- end ifmain
