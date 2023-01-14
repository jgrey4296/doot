#!/usr/bin/env python3
"""
Alternative doot cli runner, to use the doot loader
"""
##-- imports
from __future__ import annotations

import sys
import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
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
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import doot
from doit.doit_cmd import DoitMain
from doot.utils.loader import DootLoader
from doit.action import CmdAction

def main():
    result = 1
    try:
        if doot.config is None:
            doot.setup()
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
