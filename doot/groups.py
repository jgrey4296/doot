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
from doot import data_toml
from doot.utils.toml_accessor import TomlAccessError

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
    "latex_group", "gtags_group", "git_group",
    "cargo_group", "epub_group",
]


##-- defaults
defaults_group = TaskGroup("defaults",

                           )
##-- end defaults

##-- pip
try:
    data_toml.project
    from doot.builders import pip_install as pip
    pip_group = TaskGroup("pip_group",
                          pip.editlib,
                          pip.install,
                          pip.wheel,
                          pip.srcbuild,
                          pip.uninstall,
                          pip.pip_requirements,
                          pip.version)
except TomlAccessError:
    pip_group = None
##-- end pip

##-- jekyll
try:
    from doot.builders import jekyll as j_build
    from doot.docs import jekyll as j_doc
    jekyll_group = TaskGroup("jekyll_group",
                             j_build.task_jekyll_serve,
                             j_build.task_jekyll_build,
                             j_build.task_jekyll_install,
                             j_build.task_init_jekyll,
                             j_doc.GenPostTask(),
                             j_doc.GenTagsTask(),
                             )
except TomlAccessError:
    jekyll_group = None

##-- end jekyll

##-- latex
try:
    from doot.builders import latex
    latex_group = TaskGroup("latex_group",
                            latex.LatexMultiPass(),
                            latex.LatexFirstPass(),
                            latex.LatexSecondPass(),
                            latex.BibtexBuildTask(),
                            latex.BibtexConcatenateTask(),
                            latex.LatexCheck(),
                            latex.task_latex_docs,
                            latex.task_latex_install,
                            latex.task_latex_requirements,
                            latex.task_latex_rebuild,
                            )
except TomlAccessError:
    latex_group = None
##-- end latex

##-- sphinx
try:
    from doot.builders import sphinx
    sphinx_group = TaskGroup("sphinx_group",
                             sphinx.SphinxDocTask(),
                             sphinx.task_browse,
                             )
except TomlAccessError:
    sphinx_group = None
##-- end sphinx

##-- gtags
try:
    from doot.data import gtags
    gtags_group = TaskGroup("gtags_group",
                            gtags.task_tags_init,
                            gtags.task_tags
                            )
except TomlAccessError:
    gtags_group = None
##-- end gtags

##-- git
try:
    from doot.vcs import git_tasks
    git_group = TaskGroup("git group",
                          git_tasks.GitLogTask(),
                          )
except TomlAccessError:
    git_group = None
##-- end git

##-- cargo
try:
    data_toml.package
    from doot.builders import cargo
    cargo_group = TaskGroup("cargo_group",
                            cargo.task_cargo_build,
                            cargo.task_cargo_install,
                            cargo.task_cargo_test,
                            cargo.task_cargo_run,
                            cargo.task_cargo_doc,
                            cargo.task_cargo_clean,
                            cargo.task_cargo_check,
                            cargo.task_cargo_update,
                            cargo.task_rustup_show,
                            cargo.task_cargo_rename_binary,
                            cargo.task_cargo_help,
                            cargo.task_cargo_debug,
                            cargo.task_cargo_version)
except TomlAccessError:
    cargo_group = None
##-- end cargo

##-- gradle
except TomlAccessError:
    from doot.builders import gradle
    gradle_group = TaskGroup("gradle_group",
                             gradle.task_gradle_run,
                             gradle.task_gradle_build,
                             gradle.task_gradle.assemble,
                             gradle.task_gradle.check,
                             gradle.task_gradle_clean,
                             gradle.task_gradle_doc,
                             gradle.task_gradle_logging,
                             gradle.task_gradle_version,
                             gradle.task_gradle_test
                             )
except TomlAccessError:
    gradle_group = None
##-- end gradle

##-- epub
try:
    from doot.builders import epub
    epub_group = TaskGroup("epub group",
                           epub.EbookNewTask(),
                           epub.EbookCompileTask(),
                           epub.EbookConvertTask(),
                           epub.EbookZipTask(),
                           epub.EbookManifestTask(),
                           epub.EbookSplitTask(),
                           epub.EbookRestructureTask(),
                           )
except TomlAccessError:
    epub_group = None
##-- end epub
