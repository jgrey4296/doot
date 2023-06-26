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

##-- logging
logging         = logmod.root
logging.setLevel(logmod.NOTSET)
file_handler    = logmod.FileHandler(pl.Path() / "log.doot", mode='w')
file_handler.setFormatter(logmod.Formatter("{levelname} : INIT : {message}", style="{"))

stream_handler = logmod.StreamHandler()
stream_handler.setLevel(logmod.WARNING)
stream_handler.setFormatter(logmod.Formatter("{levelname}  : INIT : {message}", style="{"))

logging.addHandler(file_handler)
logging.addHandler(stream_handler)
##-- end logging

import tomler
import doot
from doot.loaders.plugin_loader import DootPluginLoader
from doot.utils.log_filter import DootAnyFilter
from doot.control.overlord import DootOverlord

def main():
    result  = 1
    errored = False
    try:
        # --- Setup
        if doot.config is None:
            doot.setup()

        setup_logging(doot.config)

        overlord  = DootOverlord(loaders={"plugin": DootPluginLoader.build(sys.argv[:])},
                                 config_filenames=[doot.constants.default_agnostic],
                                 args=sys.argv[:])

        # --- Do whatever thats been triggered
        result    = overlord(sys.argv[:])
        overlord.shutdown()

    except FileNotFoundError: # --- Handle missing files
        if not doot.constants.default_load_targets[0].exists():
            if input("No toml config data found, create stub doot.toml? _/n ") != "n":
                doot.constants.default_load_targets[0].write_text(doot.constants.toml_template.read_text())
                logging.info("Stubbed")
    except Exception as err: # --- Handle general errors
        logging.error("Error: %s", err)
        errored = True
    finally: # --- final shutdown
        announce_exit = doot.constants.announce_exit
        announce_voice = doot.constants.announce_voice
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


def setup_logging(config:Tomler):
    file_log_level    = config.on_fail("DEBUG", str).logging.file.level(wrapper=lambda x: logmod._nameToLevel.get(x, 0))
    file_log_format   = config.on_fail("{levelname} : {pathname} : {lineno} : {funcName} : {message}", str).logging.file.format()
    file_filter_names = config.on_fail([], list).logging.file.filters()

    file_handler.setLevel(file_log_level)
    file_handler.setFormatter(logmod.Formatter(file_log_format, style="{"))
    if bool(file_filter_names):
        file_handler.addFilter(DootAnyFilter(file_filter_names))

    stream_log_level    = config.on_fail("DEBUG", str).logging.stream.level(wrapper=lambda x: logmod._nameToLevel.get(x, 0))
    stream_log_format   = config.on_fail("{levelname} : {pathname} : {lineno} : {funcName} : {message}", str).logging.stream.format()
    stream_filter_names = config.on_fail([], list).logging.stream.filters()

    stream_handler.setLevel(stream_log_level)
    stream_handler.setFormatter(logmod.Formatter(stream_log_format, style="{"))
    if bool(stream_filter_names):
        stream_handler.addFilter(DootAnyFilter(stream_filter_names))


##-- ifmain
if __name__ == '__main__':
    main()
##-- end ifmain
