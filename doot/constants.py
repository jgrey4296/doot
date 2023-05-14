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

PLUGIN_TOML_PREFIX         : Final = "doot.plugins" # (project.entry-points."doot.plugins")
FRONTEND_PLUGIN_TYPES      : Final = ['command', 'reporter']
BACKEND_PLUGIN_TYPES       : Final = ['database', 'control', 'dispatch', 'runner', 'command_loader', 'task_loader', 'parser', 'action', 'tasker', 'task', 'group']

default_load_targets = [pl.Path(x) for x in ["doot.toml", "pyproject.toml", "Cargo.toml", "./.cargo/config.toml"]]
default_dooter       = pl.Path("dooter.py")

default_cmds = ["doot.cmds.help_cmd:HelpCmd",
                "doot.cmds.run_cmd:RunCmd",
                "doot.cmds.list_cmd:ListCmd",
                "doot.cmds.clean_cmd:CleanCmd",
                "doot.cmds.complete_cmd:CompleteCmd",
                "doot.cmds.server_cmd:ServerCmd",
                "doot.cmds.daemon_cmd:DaemonCmd"
    ]

default_cli_cmd = "run"
