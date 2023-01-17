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

import doot
from doot.utils.loader import DootLoader

def main():
    result = 1
    try:
        if doot.config is None:
            doot.setup()

        logging.info("Basic Doot setup loaded")
        ##-- logging setup
        file_handler.setLevel(logmod._nameToLevel[doot.config.or_get("DEBUG").tool.doot.log_level()])
        file_log_format = doot.config.or_get("{levelname} : {module} : {lineno} : {funcName} : {message}").tool.doot.log_format()
        file_handler.setFormatter(logmod.Formatter(file_log_format, style="{"))
        ##-- end logging setup

        loader    = DootLoader()
        doit_main = DoitMain(task_loader=loader, config_filenames=[doot.default_agnostic])
        result    = doit_main.run(sys.argv[1:])

        say_text = doot.config.or_get(False).tool.doot.say_on_exit()
        if bool(say_text):
            CmdAction(["say", say_text], shell=False).execute()

    except FileNotFoundError:
        if not doot.default_agnostic.exists():
            if input("No toml config data found, create stub doot.toml? _/n ") != "n":
                doot.default_agnostic.write_text(doot.toml_template.read_text())
                print("Stubbed")
        if not doot.default_dooter.exists():
            if input("No Dooter file found, create stub dooter.py? _/n ") != "n":
                doot.default_dooter.write_text(doot.dooter_template.read_text())
                print("Stubbed")


    sys.exit(result)

##-- ifmain
if __name__ == '__main__':
    main()
##-- end ifmain
