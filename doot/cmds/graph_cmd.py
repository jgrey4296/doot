#!/usr/bin/env python3
"""
Initialise a task tracker graph, convert it to a as-dot svg,
  then open an html page of it

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from collections import defaultdict
import sh

from tomlguard import TomlGuard
import doot
import doot.errors
from doot._abstract import Command_i
from doot.structs import DootParamSpec
from doot.utils.plugin_selector import plugin_selector
import networkx as nx
import matplotlib.pyplot as plt

printer                  = logmod.getLogger("doot._printer")

INDENT : Final[str]      = " "*8
tracker_target           = doot.config.on_fail("default", str).commands.run.tracker()

@doot.check_protocol
class GraphCmd(Command_i):
    _name      = "graph"
    _help      = ["Create a graph representation of the task network"]

    @property
    def param_specs(self) -> list[DootParamSpec]:
        return super().param_specs + [
            self.make_param(name="all",                                          default=True,                   desc="List all loaded tasks, by group"),
            self.make_param(name="dependencies",                                 default=False,                  desc="List task dependencies",                 prefix="--"),
            self.make_param(name="dag",       _short="D",                        default=False,                  desc="Output a DOT compatible graph of tasks", prefix="--"),
            self.make_param(name="groups",                   type=bool,          default=False,                  desc="List just the groups tasks fall into",   prefix="--"),
            self.make_param(name="by-source",                                    default=False,                  desc="List all loaded tasks, by source file",  prefix="--"),
            self.make_param(name="locations", _short="l",    type=bool,          default=False,                  desc="List all Loaded Locations"),
            self.make_param(name="internal",  _short="i",    type=bool,          default=False,                  desc="Include internal tasks (ie: prefixed with an underscore)"),
            self.make_param(name="as-dot", type=bool, default=True, desc="use dot for visualisation"),
            self.make_param(name="dot-file", prefix="--", type=str, default=None, desc="a file name to write the dot to"),
            self.make_param(name="pattern",                  type=str,           default="", positional=True,    desc="List tasks with a basic string pattern in the name"),
            ]

    def __call__(self, tasks:TomlGuard, plugins:TomlGuard):
        """List task generators"""
        logging.debug("Starting to List Jobs/Tasks")
        tracker = plugin_selector(plugins.on_fail([], list).tracker(), target=tracker_target)()

        printer.info("- Building Task Dependency Network")
        for task in tasks.values():
            tracker.add_task(task)

        printer.info("- Task Dependency Network Built")
        if not hasattr(tracker, "dep_graph"):
            logging.warning("Can't get a dep_graph for the tracker")

        graph = tracker.dep_graph
        graph.remove_node(tracker._root_name)

        match doot.args.cmd.args:
            case {"as-dot": True, "dot-file": loc} if bool(loc):
                dot_obj = self.to_dot(graph)
                loc = doot.locs[loc]
                match loc.suffix:
                    case ".jpg":
                        dot_obj.write_jpg(loc)
                    case ".png":
                        dot_obj.write_png(loc)
                    case ".svg":
                        dot_obj.write_svg(loc)
                    case ".dot":
                        loc.write_text(str(dot_obj))
                printer.info("-- Dot written to: %s", loc)

            case {"as-dot": True}:
                dot_obj = self.to_dot(graph)
                printer.info(str(dot_obj))

    def draw_pyplot(self, graph, loc):
        wrapped = self._relabel_node_names(graph)
        nx.draw(wrapped)
        plt.show()

    def to_dot(self, graph) -> pydot.Dot:
        printer.warning("TODO: dot style")
        wrapped = self._relabel_node_names(graph)
        return nx.nx_pydot.to_pydot(wrapped)


    def _relabel_node_names(self, graph):
        """
          By default, tasks are in the form group::name
          as-dot doesn't like nodes of that form, so wrap them in quotes.
        """
        mod_dict = {x: f'"{x}"' for x in graph.nodes}
        return nx.relabel_nodes(graph, mod_dict)
