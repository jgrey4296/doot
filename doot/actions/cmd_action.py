##-- imports
from __future__ import annotations

# import abc
# import datetime
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

import doot
from doot._abstract.action import Action_p

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


class DootCmdAction(Action_p):
    """
    CmdAction that doesn't call it's python callable multiple times
    (for a single call of `execute`)
    """

    def __str__(self):
        return f"Cmd: {self._action}"

    @property
    def action(self):
        match self._action:
            case str() | list():
                return self._action
            case [ref, args, kw]:
                # action can be a callable that returns a string command
                kwargs = self._prepare_kwargs(self.task, ref, args, kw)
                return ref(*args, **kwargs)
            case _ as ref:
                args, kw = (), {}
                kwargs = self._prepare_kwargs(self.task, ref, args, kw)
                return ref(*args, **kwargs)

    def expand_action(self):
        """Expand action using task meta informations if action is a string.
        Convert `Path` elements to `str` if action is a list.
        @returns: string -> expanded string if action is a string
                    list - string -> expanded list of command elements
        """
        action_prepped = self.action

        if not self.task:
            return action_prepped

        if isinstance(action_prepped, list):
            # cant expand keywords if action is a list of strings
            action = []
            for element in action_prepped:
                if isinstance(element, str):
                    action.append(element)
                elif isinstance(element, pl.PurePath):
                    action.append(str(element))
                else:
                    msg = ("%s. CmdAction element must be a str "
                            "or Path from pathlib. Got '%r' (%s)")
                    raise InvalidTask(msg % (self.task.name, element, type(element)))
            return action

        subs_dict = {
            'targets'      : " ".join(self.task.targets),
            'dependencies' : " ".join(self.task.file_dep),
        }

        # dep_changed is set on get_status()
        # Some commands (like `clean` also uses expand_args but do not
        # uses get_status, so `changed` is not available.
        if self.task.dep_changed is not None:
            subs_dict['changed'] = " ".join(self.task.dep_changed)

        # task option parameters
        subs_dict.update(self.task.options)
        # convert positional parameters from list space-separated string
        if self.task.pos_arg:
            if self.task.pos_arg_val:
                pos_val = ' '.join(self.task.pos_arg_val)
            else:
                pos_val = ''
            subs_dict[self.task.pos_arg] = pos_val

        if self.STRING_FORMAT == 'old':
            return action_prepped % subs_dict
        elif self.STRING_FORMAT == 'new':
            return action_prepped.format(**subs_dict)
        else:
            assert self.STRING_FORMAT == 'both'
            return action_prepped.format(**subs_dict) % subs_dict
