#/usr/bin/env python3
"""
Parameterless task groups
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
    "pip_group", "jekyll_group", "sphinx_group",
    "latex_group", "gtags_group",
]

##-- defaults
defaults_group = TaskGroup("defaults",

                           )
##-- end defaults

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

##-- jekyll
from doot.builders import jekyll as j_build
from doot.docs import jekyll as j_doc
jekyll_group = TaskGroup("jekyll_group",
                         j_build.task_jekyll_serve,
                         j_build.task_jekyll_build,
                         j_build.task_jekyll_install,
                         j_build.task_init_jekyll,
                         j_build.jekyll_check_build,
                         j_build.jekyll_check_src,
                         j_doc.jekyll_check_posts,
                         j_doc.jekyll_check_tags,
                         j_doc.GenPostTask(),
                         j_doc.GenTagsTask(),
                         )

##-- end jekyll

##-- latex
from doot.builders import latex
latex_group = TaskGroup("latex_group",
                        latex.task_latex_docs,
                        latex.task_latex_install,
                        latex.task_latex_requirements,
                        latex.task_latex_rebuild,
                        )

##-- end latex

##-- sphinx
from doot.builders import sphinx
sphinx_group = TaskGroup("sphinx_group",
                         sphinx.SphinxDocTask(),
                         sphinx.task_browse,
                         sphinx.check_dir)

##-- end sphinx

##-- gtags
from doot.data import gtags
gtags_group = TaskGroup("gtags_group",
                        gtags.task_tags_init,
                        gtags.task_tags
                        )
##-- end gtags

##-- git
from doot.vcs import git_tasks
git_group = TaskGroup("git group",
                      git_tasks.GitLogTask(),
                      )
##-- end git
