#!/usr/bin/env python3
"""
Tasks for ensuring programs exist
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

import shutil

brew          = shutil.which("brew")
cargo         = shutil.which("cargo")
clingo        = shutil.which("clingo")
datadata      = shutil.which("datadata")
dot           = shutil.which("dot")
ebook_convert = shutil.which("ebook-convert")
godot         = shutil.which("godot")
gradle        = shutil.which("gradle")
gtags         = shutil.which("gtags")
jekyll        = shutil.which("jekyll")
pdflatex      = shutil.which("pdflatex")
pdftk         = shutil.which("pdftk")
pip           = shutil.which("pip")
plantuml      = shutil.which("plantuml")
poetry        = shutil.which("poetry")
ruby          = shutil.which("ruby")
sphinix       = shutil.which("sphinix")
trang         = shutil.which("trang")
xml           = shutil.which("xml")
xsdata        = shutil.which("xsdata")
xsdata        = shutil.which("xsdata")

def task_xsdata_config():
    return {
        "basename" : "_xsdata::config",
        "actions" : [ "xsdata init-config" ],
        "targets" : [ ".xsdata.xml" ],
    }


def task_ebookconvert_version():
    return {
        "basename" : "_ebookconvert::exists",
        "actions" : [ "ebook-convert --version" ],
    }

def task_pip_version():
    return {
        "basename" : "_pip::exists",
        "actions" : [ "pip --version" ],
    }

def task_cargo_version():
    return {
        "basename" : "_cargo::exists",
        "actions" : [ "cargo --version" ],
    }

def task_latex_version():
    return {
        "basename" : "_latex::exists",
        "actions" : [ "pdflatex --version", "bibtex --version" ],
    }

def task_ruby_version():
    return {
        "basename" : "_ruby::exists",
        "actions" : [ "ruby --version" ],
    }

def task_jekyll_version():
    return {
        "basename" : "_jekyll::exists",
        "actions" : [ "jekyll --version" ],
    }

def task_brew_version():
    return {
        "basename" : "_brew::exists",
        "actions" : [ "brew --version" ],
    }

def task_pdftk_version():
    return {
        "basename" : "_pdftk::exists",
        "actions" : [ "pdftk --version" ],
    }

def task_gradle_version():
    return {
        "basename" : "_gradle::exists",
        "actions" : [ "gradle --version" ],
    }

def task_sphinx_version():
    return {
        "basename" : "_sphinx::exists",
        "actions" : [ "sphinx-build --version" ],
    }

def task_godot_version():
    return {
        "basename" : "_godot::exists",
        "actions" : ["godot --version"],
    }

def task_poetry_version():
    return {
        "basename" : "_poetry::exists",
        "actions" : ["poetry --version"],
    }

def task_gtags_version():
    return {
        "basename" : "_gtags::exists",
        "actions" : ["gtags --version", "global --version"],
    }


def task_xml_version():
        return {
        "basename" : "_xml::exists",
            "actions" : ["xml --version"],
    }


def task_trang_version():
        return {
            "basename" : "_trang::exists",
            "actions" : ["which trang"] ,
        }

def task_plantuml_version():
    return {
        "basename" : "_plantuml::exists",
        "actions" : ["plantuml -version"],
    }

def task_git_version():
    return {
        "basename" : "_git::exists",
        "actions" : ["git --version"],
    }

def task_dot_version():
    return {
        "basename" : "_dot::exists",
        "actions" : ["dot -V"],
    }

def task_clingo_version():
    return {
        "basename" : "_clingo:exists",
        "actions" : [ "clingo -v" ],
    }
