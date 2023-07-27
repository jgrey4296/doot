#!/usr/bin/env python3
"""
A Singleton for storing stub toml fragments which can be provided to the user
"""
##-- imports
from __future__ import annotations

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
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

class GenToml:
    generators : ClassVar[dict]     = {}
    gen_file   : ClassVar[pl.Path]  = pl.Path("doot_gen.toml")
    gen_hashes : Classvar[set[int]] = set()

    @staticmethod
    def add_generator(name : str, generate : Callable):
        # GenToml.generators[name] = generate
        task = {
            "basename" : "generate::toml",
            "name"     : name,
            "actions"  : [ (GenToml.add_text, [name, generate]) ],
            "file_dep" : [ GenToml.gen_file],
            "setup"    : ["generate::toml:setup"],
            }
        GenToml.generators[name] = task

    @staticmethod
    def gen_toml_tasks():
        logging.info("Building GenToml Auto Tasks: %s", list(GenToml.generators.keys()))
        for task in GenToml.generators.values():
            yield task

        # Setup
        yield {
            "basename" : "generate::toml",
            "name"     : "setup",
            "actions"  : [ GenToml.prep_gen_toml ],
            "targets"  : [ GenToml.gen_file ],
            "clean"    : True,
        }
        # Top
        yield {
            "basename" : "generate::toml",
            "name"  : None,
            "task_dep" : [f"generate::toml:{name}" for name in GenToml.generators.keys()],
        }

    @staticmethod
    def prep_gen_toml():
        text = ["## Generated default toml data",
                "## copy this into your",
                "## doot.toml file",
                ""]
        GenToml.gen_file.write_text("\n".join(text))

    @staticmethod
    def add_text(name, generate:callable):
        text = generate()
        text_hash = hash(text)
        if text_hash in GenToml.gen_hashes:
            return

        GenToml.gen_hashes.add(text_hash)
        with open(GenToml.gen_file, 'a') as f:
            f.write(f"##-- generated {name} config\n")
            f.write(text + "\n")
            f.write(f"##-- end generated {name} config\n")
