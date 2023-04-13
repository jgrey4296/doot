#!/usr/bin/env python3
"""

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

import doot

dot_scale  = doot.config.on_fail(72.0, float).dot_graph.scale()
dot_layout = doot.config.on_fail("neato", str).dot_graph.layout()
dot_ext    = doot.config.on_fail("png", str).dot_graph.ext()

class DotMixin:

    def dot_params(self):
        return [
            { "name" : "layout", "type": str,   "short": "l", "default": dot_layout},
            { "name" : "scale" , "type": float, "short": "s", "default": dot_scale},
            { "name" : "ext",    "type": str,   "short": "e", "default": dot_ext}
        ]

    def dot_image(self, src, dst) -> list:
        return [
            "dot", target,
            f"-T{self.args['ext']}",
            f"-K{self.args['layout']}",
            f"-s{self.args['scale']}",
            "-o", fpath
        ]

    def dot_graph(self):
        """
        https://graphviz.org/doc/info/command.html

        -c<n>         : cycle
        -C<x,y>       : cylinder
        -g[f]<h,w>    : grid (folded if f is used)
        -G[f]<h,w>    : partial grid (folded if f is used)
        -h<x>         : hypercube
        -k<x>         : complete
        -b<x,y>       : complete bipartite
        -B<x,y>       : ball
        -i<n>         : generate <n> random
        -m<x>         : triangular mesh
        -M<x,y>       : x by y Moebius strip
        -n<prefix>    : use <prefix> in node names ("")
        -N<name>      : use <name> for the graph ("")
        -o<outfile>   : put output in <outfile> (stdout)
        -p<x>         : path
        -r<x>,<n>     : random graph
        -R<n>         : random rooted tree on <n> vertices
        -s<x>         : star
        -S<x>         : 2D sierpinski
        -S<x>,<d>     : <d>D sierpinski (<d> = 2,3)
        -t<x>         : binary tree
        -t<x>,<n>     : n-ary tree
        -T<x,y>       : torus
        -T<x,y,t1,t2> : twisted torus
        -w<x>         : wheel
        -d            : directed graph
        -v            : verbose mode
        -?            : print usage
        """
        return [ "gvgen" ]
