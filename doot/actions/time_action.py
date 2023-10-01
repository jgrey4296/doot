## base_action.py -*- mode: python -*-
##-- imports
from __future__ import annotations

# import abc
import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
# from uuid import UUID, uuid1
# from weakref import ref

# from bs4 import BeautifulSoup
# import boltons
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
# import more_itertools as itzplus
# import networkx as nx
# import numpy as np
# import pandas
# import pomegranate as pom
# import pony import orm
# import pronouncing
# import pyparsing as pp
# import rich
# import seaborn as sns
# import sklearn
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
# import spacy # nlp = spacy.load("en_core_web_sm")

##-- end imports

printer = logmod.getLogger("doot._printer")

from time import sleep
import sh
import doot
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p

@doot.check_protocol
class TimeAction(Action_p):
    """
    A Simple Action that announces the time
    Subclass this and override __call__ for your own actions.
    The arguments of the action are held in self.spec
    __call__ is passed a *copy* of the task's state dictionary

    """
    announce_args = ["-v", "Moira", "-r", "50", "The Time Is "]
    time_format   = "%H:%M"

    def __str__(self):
        return f"Base Action: {self.spec.args}"

    def expand_str(self, val, state):
        return val.format_map(state)

    def _current_time(self) -> str:
        now = datetime.datetime.now()
        return now.strftime(self.time_format)


    def __call__(self, spec, task_state_copy:dict) -> dict|bool|None:
        try:
            cmd    = sh.say
            args   = (spec.args or self.announce_args) + [self._current_time()]
            if spec.kwargs.on_fail(False, bool).wait():
                sleep(10)
            result = cmd(*args, _return_cmd=True, _bg=spec.kwargs.on_fail(False, bool).background())
            assert(result.exit_code == 0)
            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, cmd, args)
            printer.info("%s", result, extra={"colour":"reset"})
            return True
        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], spec.args)
            return False
        except sh.ErrorReturnCode:
            printer.error("Shell Command '%s' exited with code: %s for args: %s", spec.args[0], result.exit_code, spec.args)
            return False
