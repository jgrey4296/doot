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
from doot.utils.toml_access import TomlAccessError, TomlAccess
from doot import build_dir, data_toml, temp_dir, doc_dir, src_dir

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
    data_toml.tool.doot.pip
    from doot.builders import pip_install as pip
    from doot.code import python as py_tasks
    pip_group = TaskGroup("pip_group",
                          pip.editlib,
                          pip.install,
                          pip.wheel,
                          pip.srcbuild,
                          pip.uninstall,
                          pip.pip_requirements,
                          pip.version,
                          pip.upgrade,
                          py_tasks.InitPyGlobber(),
                          py_tasks.PyLintTask(),
                          py_tasks.PyTestGlob(),
                          )
except TomlAccessError:
    pip_group = None
##-- end pip

##-- jekyll
try:
    data_toml.tool.doot.jekyll
    from doot.builders import jekyll as j_build
    from doot.docs import jekyll as j_doc
    jekyll_config = pl.Path("jekyll.toml")
    jekyll_toml   = TomlAccess.load("jekyll.toml")
    jekyll_src    = pl.Path(jekyll_toml.or_get("docs/site").source())
    jekyll_dest   = pl.Path(jekyll_toml.or_get(build_dir/"jekyll").destination())

    j_build.build_jekyll_checks(jekyll_dest, jeykll_src)
    jekyll_group = TaskGroup("jekyll_group",
                             j_build.task_jekyll_serve,
                             j_build.task_jekyll_build(jekyll_config),
                             j_build.task_jekyll_install(jekyll_config),
                             j_build.task_init_jekyll(jekyll_config, jekyll_src),
                             j_doc.GenPostTask(),
                             j_doc.GenTagsTask(),
                             )
except TomlAccessError:
    jekyll_group = None
except FileNotFoundError:
    jekyll_group = None

##-- end jekyll

##-- latex
try:
    data_toml.tool.doot.tex
    from doot.builders import latex
    tex_src_dir  = doc_dir   / "tex"
    tex_dir      = build_dir / "tex"
    tex_temp_dir = temp_dir  / "tex"
    interaction_mode = data_toml.or_get("nonstopmode").tool.doot.tex.interaction()
    latex.build_latex_check(tex_dir, tex_temp_dir)
    latex_group = TaskGroup("latex_group",
                            latex.LatexMultiPass([tex_src_dir], tex_dir),
                            latex.LatexFirstPass([tex_src_dir], tex_temp_dir, tex_dir, interaction_mode),
                            latex.LatexSecondPass([tex_src_dir], tex_temp_dir, tex_dir),
                            latex.BibtexBuildTask([tex_src_dir], tex_temp_dir, tex_dir),
                            latex.BibtexConcatenateTask([tex_src_dir], tex_temp_dir),
                            latex.LatexCheck([tex_src_dir], tex_temp_dir),
                            latex.task_latex_docs,
                            latex.task_latex_install(),
                            latex.task_latex_requirements(),
                            latex.task_latex_rebuild,
                            )
except TomlAccessError:
    latex_group = None
##-- end latex

##-- sphinx
try:
    data_toml.tool.doot.sphinx
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
    data_toml.tool.doot.gtags
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
    data_toml.tool.doot.git
    from doot.vcs import git_tasks
    git_group = TaskGroup("git group",
                          git_tasks.GitLogTask(),
                          )
except TomlAccessError:
    git_group = None
##-- end git

##-- cargo
try:
    data_toml.tool.doot.cargo
    data_toml.package
    bin_file = data_toml.package.name
    try:
        bin_file = data_toml.bin[0].name
    except TomlAccessError:
        pass

    from doot.builders import cargo
    cargo_group = TaskGroup("cargo_group",
                            cargo.task_cargo_build(build_dir, ("bin", bin_file)),
                            cargo.task_cargo_build(build_dir, ("bin", bin_file), profile="release"),
                            cargo.task_cargo_mac_lib(build_dir, package=data_toml.package.name),
                            cargo.task_cargo_install,
                            cargo.task_cargo_test(("bin", "bin_file")),
                            cargo.task_cargo_run,
                            cargo.task_cargo_doc,
                            cargo.task_cargo_clean,
                            cargo.task_cargo_check,
                            cargo.task_cargo_update,
                            cargo.task_rustup_show,
                            cargo.task_cargo_help,
                            cargo.task_cargo_debug(build_dir, target=("bin", bin_file)),
                            cargo.task_cargo_version)
except TomlAccessError:
    cargo_group = None
##-- end cargo

##-- gradle
except TomlAccessError:
    data_toml.tool.doot.gradle
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
    data_toml.tool.doot.epub
    epub_build_dir   = build_dir / "epub"
    epub_working_dir = doc_dir / "epub"
    epub_orig_dir    = doc_dir / "orig" / "epub"
    epub_zip_dir     = temp_dir / "epub"
    from doot.builders import epub
    epub.build_epub_check(epub_working_dir, epub_build_dir, epub_orig_dir, epub_zip_dir)
    epub_group = TaskGroup("epub group",
                           epub.EbookNewTask(),
                           epub.EbookCompileTask([epub_working_dir]),
                           epub.EbookConvertTask([epub_working_dir]),
                           epub.EbookZipTask([epub_working_dir], epub_zip_dir),
                           epub.EbookManifestTask([epub_working_dir]),
                           epub.EbookSplitTask([epub_orig_dir]),
                           epub.EbookRestructureTask([epub_working_dir]),
                           epub.EbookNewTask([epub_working_dir])
                           )
except TomlAccessError:
    epub_group = None
##-- end epub
