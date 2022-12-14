#/usr/bin/env python3
"""

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
from doot.utils.task_group import TaskGroup

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

__all__ = [
    "pip_group"
]

##-- defaults
defaults_group = TaskGroup("defaults",

                           )
##-- end defaults

##-- jekyll
from doot.builders import jekyll
jekyll_group = TaskGroup("jekyll_group",
                         jekyll.task_jekyll_serve,
                         jekyll.task_jekyll_build)



##-- end jekyll

##-- latex
from doot.builders import latex
latex_group = TaskGroup("latex_group",
                        latex.task_latex_build,
                        latex.task_bibtex_build,
                        latex.task_latex_docs,
                        latex.task_latex_install_dependencies,
                        )

##-- end latex

##-- pdf
pdf_group = TaskGroup("pdf_group",

                      )


##-- end pdf

##-- sphinx
from doot.builders import sphinx
sphinx_group = TaskGroup("sphinx_group",
                         sphinx.task_sphinx, sphinx.task_browse)

##-- end sphinx

##-- python
python_group = TaskGroup("python",

                         )

##-- end python

##-- poetry
from doot.builders import poetry_install as poetry
poetry_group = TaskGroup("poetry_group",
                         poetry.install,
                         poetry.wheel,
                         poetry.requirements)

##-- end poetry

##-- pip
from doot.builders import pip_install as pip
pip_group = TaskGroup("pip_group",
                      pip.editlib,
                      pip.install,
                      pip.wheel,
                      pip.srcbuild,
                      pip.uninstall,
                      pip.pip_requirements,
                      pip.version)

##-- end pip

##-- conda
conda_group = TaskGroup("conda_group",

                        )
##-- end conda

##-- cargo
from doot.builders import cargo
cargo_group = TaskGroup("cargo_group",
                        cargo.task_cargo_check,
                        cargo.task_cargo_init,
                        cargo.task_rustup,
                        cargo.task_cargo_docs,
                        cargo.task_cargo_help,
                        cargo.task_cargo_debug,
                        cargo.task_cargo_release,
                        cargo.task_cargo_test,
                        cargo.task_cargo_version)
##-- end cargo

##-- erlang
erlang_group = TaskGroup("erlang_group",

                        )
##-- end erlang

##-- ruby
ruby_group = TaskGroup("ruby_group",

                       )
##-- end ruby

##-- godot
godot_group = TaskGroup("godot_group",

                        )
##-- end godot

##-- gradle
gradle_group = TaskGroup("gradle_group",

                         )
##-- end gradle

##-- grunt
grunt_group = TaskGroup("grunt group",

                        )
##-- end grunt

##-- homebrew
brew_group = TaskGroup("brew group",

                       )
##-- end homebrew

##-- epub
epub_group = TaskGroup("epub group",

                       )
##-- end epub

##-- xml
xml_group = TaskGroup("xml_group",

                      )
##-- end xml

##-- json
json_group = TaskGroup("json group",

                       )
##-- end json

##-- gtags
gtags_group = TaskGroup("gtags_group",

                        )
##-- end gtags

##-- plantuml
plantuml_group = TaskGroup("plantuml_group",

                           )
##-- end plantuml

##-- git
git_group = TaskGroup("git group",

                      )
##-- end git
