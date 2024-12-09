#!/usr/bin/env python3
"""
Initialise a task tracker graph, convert it to a as-dot svg,
  then open an html page of it

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from collections import defaultdict
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
import matplotlib.pyplot as plt
import networkx as nx
import sh
from jgdv.structs.chainguard import ChainGuard
from jgdv.cli.param_spec import ParamSpec

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.cmds.base_cmd import BaseCommand
from doot.structs import DKey, TaskName, TaskArtifact
from doot.utils.plugin_selector import plugin_selector

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
cmd_l   = doot.subprinter("cmd")
fail_l  = doot.subprinter("fail")
##-- end logging

INDENT : Final[str]      = " "*8
tracker_target           = doot.config.on_fail("default", str).settings.commands.run.tracker()
ROOT_COLOR : Final[str] = "green"
NODE_COLOR : Final[str] = "#8db6cd"

DRAW_OPTIONS : Final[dict] = dict(
    with_labels=True,
    arrowstyle="->",
    node_color="green",
    verticalalignment="baseline",
    bbox={"edgecolor": "k", "facecolor": "white", "alpha": 0.5 },
    )


@doot.check_protocol
class GraphCmd(BaseCommand):
    _name      = "graph"
    _help      = ["Create a graph representation of the task network"]

    @property
    def param_specs(self) -> list[ParamSpec]:
        return super().param_specs + [
            self.build_param(name="dot",       _short="D",                        default=False,                  desc="Output a DOT compatible graph of tasks", prefix="--"),
            self.build_param(name="internal",  _short="i",    type=bool,          default=False,                  desc="Include internal tasks (ie: prefixed with an underscore)"),
            self.build_param(name="as-dot",                   type=bool,          default=True,                   desc="use dot for visualisation"),
            self.build_param(name="draw", prefix="--",        type=bool,          default=False,                  desc="Draw the Graph in a UI with plt"),
            self.build_param(name="dot-file", prefix="--",    type=str,           default=None,                   desc="a file name to write the dot to. uses key expansion"),
            ]

    def __call__(self, tasks:ChainGuard, plugins:ChainGuard):
        """List task generators"""
        logging.debug("Starting to Graph Jobs/Tasks Network")
        tracker = plugin_selector(plugins.on_fail([], list).tracker(), target=tracker_target)()
        if not hasattr(tracker, "network"):
            fail_l.error("Can't get a dep_graph for the tracker")
            return False

        match self._build_graph(tracker, tasks):
            case None:
                fail_l.error("Graph Could not be build")
            case nx.DiGraph() as x:
                graph = x

        match doot.args.cmd.args:
            case {"draw": True}:
                self.draw_pyplot(graph)
            case {"as-dot": True, "dot-file": loc_key} if bool(loc_key):
                cmd_l.info("Expanding Location: %s", loc_key)
                loc_key = DKey(loc_key, mark=DKey.mark.PATH)
                loc = loc_key.expand()
                cmd_l.info("Target Location Expanded: %s", loc)
                self.write_dot_image(graph, loc)
            case {"as-dot": True}:
                dot_obj = self.to_dot(graph)
                cmd_l.info("# ---- Raw Dot: ")
                cmd_l.info(str(dot_obj))
                cmd_l.info("# ---- End of Raw Dot")

    def _build_graph(self, tracker, tasks) -> None|nx.DiGraph:
        cmd_l.info("- Adding Tasks to temp tracker")
        for task in tasks.values():
            new_id = tracker.queue_entry(task)
            tracker.connect(tracker._root_node, new_id)
        cmd_l.info("- Building Dependency Network")
        tracker.build_network(sources=True)
        cmd_l.info("- Validating Dependency Network")
        tracker.validate_network(strict=True)

        cmd_l.info("- Task Dependency Network Built")


        if not bool(tracker.network.nodes) or not bool(tracker.network.edges):
            fail_l.error("Graph is Empty")
            return None

        return tracker.network

    def write_dot_image(self, graph, loc):
        dot_obj = self.to_dot(graph)
        match loc.suffix:
            case ".jpg":
                dot_obj.write_jpg(loc)
            case ".png":
                dot_obj.write_png(loc)
            case ".svg":
                dot_obj.write_svg(loc)
            case ".dot":
                loc.write_text(str(dot_obj))
            case x:
                fail_l.error("Unknown Location Suffix: %s", x)
                return False
        cmd_l.info("-- Dot written to: %s", loc)

    def draw_pyplot(self, graph):
        """ Actually display the graph """
        wrapped = self._relabel_node_names(graph)
        opts = {}
        opts.update(DRAW_OPTIONS)
        opts['node_color'] = [ROOT_COLOR if i == 0 else NODE_COLOR for i,x in enumerate(wrapped.nodes)]
        nx.draw_networkx(wrapped, **opts)
        plt.show()

    def to_dot(self, graph) -> pydot.Dot:
        """ Convert a networkx graph to a Dot object"""
        cmd_l.info("Converting to a dot suitable format")
        wrapped = self._relabel_node_names(graph)
        return nx.nx_pydot.to_pydot(wrapped)

    def _relabel_node_names(self, graph):
        """
          By default, tasks are in the form group::name
          dot doesn't like nodes of that form, so wrap them in quotes.
        """
        mod_dict = {} # {x: f'"{x.pop()}"' for x in graph.nodes}
        for key in graph.nodes.keys():
            match key:
                case TaskName():
                    mod_dict[key] = f'"{key.pop()}"'
                case TaskArtifact():
                    mod_dict[key] = f'"{key}"'

        return nx.relabel_nodes(graph, mod_dict)
