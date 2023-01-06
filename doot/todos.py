#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##-- conda


##-- end conda

##-- erlang
# https://rebar3.org/docs/getting-started/
# https://hex.pm/docs/usage
# https://hexdocs.pm/mix/Mix.html
##-- end erlang

##-- ruby
# https://guides.rubygems.org/
##-- end ruby

##-- grunt
# https://gruntjs.com/getting-started
##-- end grunt

##-- homebrew

##-- end homebrew

##-- poetry
# https://python-poetry.org/docs/cli/
# TODO add increment version tasks, plus update __init__.py

install      = CmdTask("poetry", "install")
wheel        = CmdTask("poetry", "build", "--format", "wheel")
requirements = CmdTask("poetry", "lock")

# TODO poetry check

##-- end poetry

##-- adb

##-- end adb

##-- repl
def task_start_repl():
    pass
##-- end repl

##-- rust

##-- end rust

##-- encoding
# file -I {}
# iconv -f {enc} -t {enc} {} > conv-{}
class UTF8EncodeTask:

    def __init__(self, globs, encoding="utf8", name="default", **kwargs):
        self.create_doit_tasks = self.build
        self.globs             = globs
        self.kwargs            = kwargs
        self.default_spec      = { "basename" : f"utf8::{name}" }
        self.encoding          = encoding

    def convert(self):
        base = pl.Path(".")
        for glob in globs:
            for fpath in base.glob(glob):
                if not fpath.is_file():
                    continue


    def build(self):
        raise NotImplementedError()
        task_desc = self.default_spec.copy()
        task_desc.update(self.kwargs)
        task_desc.update({
            "actions"  : [ self.mkdir ],
        })
        return task_desc


##-- end encoding

##-- encrypt

##-- end encrypt

##-- file moving

##-- end file moving

##-- clips

##-- end clips

##-- coq

##-- end coq

##-- prolog

##-- end prolog

##-- soar

##-- end soar

##-- z3

##-- end z3

##-- haskell

##-- end haskell

##-- csharp

##-- end csharp
