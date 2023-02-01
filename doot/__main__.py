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
file_handler.setFormatter(logmod.Formatter("PRE_SETUP : {message}", style="{"))
logging.addHandler(file_handler)
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

        logging.info("Basic Doot setup loaded")
        ##-- logging setup
        file_handler.setLevel(logmod._nameToLevel[doot.config.on_fail("DEBUG", str).tool.doot.log_level()])
        file_log_format = doot.config.on_fail("{levelname} : {pathname} : {lineno} : {funcName} : {message}", str).tool.doot.log_format()
        file_handler.setFormatter(logmod.Formatter(file_log_format, style="{"))
        log_filter_names = doot.config.on_fail(["doot"], list).tool.doot.log_filters()
        l_filter = DootAnyFilter(log_filter_names)
        file_handler.addFilter(l_filter)
        logging.info("Log Filter Regex: %s", l_filter.name_re)
        ##-- end logging setup

        loader    = DootLoader()
        doit_main = DoitMain(task_loader=loader, config_filenames=[doot.default_agnostic])
        result    = doit_main.run(sys.argv[1:])

        defaulted_locs = doot.DootLocData.report_defaulted()
        defaulted_toml = tomler.Tomler.report_defaulted()

        with open("_doot_defaults.toml", 'w') as f:
            f.write("# default values used:\n")
            f.write("\n".join(defaulted_toml) + "\n\n")
            f.write("[tool.doot.directories]\n")
            f.write("\n".join(defaulted_locs))


    except FileNotFoundError:
        if not doot.default_agnostic.exists():
            if input("No toml config data found, create stub doot.toml? _/n ") != "n":
                doot.default_agnostic.write_text(doot.toml_template.read_text())
                print("Stubbed")
        if not doot.default_dooter.exists():
            if input("No Dooter file found, create stub dooter.py? _/n ") != "n":
                doot.default_dooter.write_text(doot.dooter_template.read_text())
                print("Stubbed")
    except Exception as err:
        print("Error: ", err, file=sys.stderr)
        errored = True
    finally:
        say_on_exit = False
        voice       = "Moira"
        if doot.config is not None:
            say_on_exit = doot.config.on_fail(False, bool|str).tool.doot.say_on_exit()
            voice       = doot.config.on_fail(voice, str).tool.doot.voice()
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
