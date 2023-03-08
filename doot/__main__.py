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

std_handler = logmod.StreamHandler()
std_handler.setLevel(logmod.WARNING)
std_handler.setFormatter(logmod.Formatter("{levelname}  : INIT : {message}", style="{"))

logging.addHandler(file_handler)
logging.addHandler(std_handler)
##-- end logging

from doit.action import CmdAction
from doit.doit_cmd import DoitMain

import tomler
import doot
from doot.utils.loader import DootLoader
from doot.utils.log_filter import DootAnyFilter

def main():
    result  = 1
    errored = False
    try:
        if doot.config is None:
            doot.setup()

        logging.debug("Basic Doot setup loaded")
        ##-- logging setup
        file_log_level    = doot.config.on_fail("DEBUG", str).logging.file.level(wrapper=lambda x: logmod._nameToLevel.get(x, 0))
        file_log_format   = doot.config.on_fail("{levelname} : {pathname} : {lineno} : {funcName} : {message}", str).logging.file.format()
        file_filter_names = doot.config.on_fail([], list).logging.file.filters()

        file_handler.setLevel(file_log_level)
        file_handler.setFormatter(logmod.Formatter(file_log_format, style="{"))
        if bool(file_filter_names):
            file_handler.addFilter(DootAnyFilter(file_filter_names))

        stream_log_level    = doot.config.on_fail("DEBUG", str).logging.stream.level(wrapper=lambda x: logmod._nameToLevel.get(x, 0))
        stream_log_format   = doot.config.on_fail("{levelname} : {pathname} : {lineno} : {funcName} : {message}", str)..logging.stream.format()
        stream_filter_names = doot.config.on_fail([], list)..logging.stream.filters()

        std_handler.setLevel(stream_log_level)
        std_handler.setFormatter(logmod.Formatter(stream_log_format, style="{"))
        if bool(stream_filter_names):
            std_handler.addFilter(DootAnyFilter(stream_filter_names))
        ##-- end logging setup

        loader    = DootLoader()
        doit_main = DoitMain(task_loader=loader, config_filenames=[doot.default_agnostic])
        result    = doit_main.run(sys.argv[1:])

        defaulted_locs = doot.DootLocData.report_defaulted()
        defaulted_toml = tomler.Tomler.report_defaulted()

        with open("_doot_defaults.toml", 'w') as f:
            f.write("# default values used:\n")
            f.write("\n".join(defaulted_toml) + "\n\n")
            f.write("[.directories]\n")
            f.write("\n".join(defaulted_locs))


    except FileNotFoundError:
        if not doot.default_agnostic.exists():
            if input("No toml config data found, create stub doot.toml? _/n ") != "n":
                doot.default_agnostic.write_text(doot.toml_template.read_text())
                logging.info("Stubbed")
        if not doot.default_dooter.exists():
            if input("No Dooter file found, create stub dooter.py? _/n ") != "n":
                doot.default_dooter.write_text(doot.dooter_template.read_text())
                logging.info("Stubbed")
    except Exception as err:
        logging.error("Error: ", err)
        errored = True
    finally:
        say_on_exit = False
        voice       = "Moira"
        if doot.config is not None:
            say_on_exit = doot.config.on_fail(False, bool|str)..notify.say_on_exit()
            voice       = doot.config.on_fail(voice, str)..notify.voice()
        match errored, say_on_exit:
            case False, str() as say_text:
                cmd = CmdAction(["say", "-v", voice, "-r", "50", say_text], shell=False)
            case False, True:
                cmd = CmdAction(["say", "-v", voice, "-r", "50", "Doot Has Finished"], shell=False)
            case True, True|str():
                cmd = CmdAction(["say", "-v", voice, "-r", "50", "Doot Encountered a problem"])
            case _:
                cmd = None
        if cmd is not None:
            cmd.execute()

        sys.exit(result)

##-- ifmain
if __name__ == '__main__':
    main()
##-- end ifmain
