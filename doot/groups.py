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
from doot import data_toml, doot_dirs
from doot.utils.dir_data import DootDirs

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

__all__ = [ "defaults_group",
    "pip_group", "jekyll_group", "sphinx_group",
    "latex_group", "gtags_group", "git_group",
    "cargo_group", "epub_group",
]


##-- defaults
try:
    from doot.files import listall
    doot_dirs.add_extra({ "visual" : doot_dirs.docs / "visual" })

    defaults_group = TaskGroup("defaults",
                               listall.task_list_target("src",     doot_dirs.src,      doot_dirs),
                               listall.task_list_target("data",    doot_dirs.data,     doot_dirs),
                               listall.task_list_target("docs",    doot_dirs.docs,     doot_dirs),
                               listall.task_list_target("build",   doot_dirs.build,    doot_dirs),
                               listall.task_list_target("temp",    doot_dirs.temp,     doot_dirs),
                               listall.task_list_target("codegen", doot_dirs.codegen,  doot_dirs),
                               )

except TomlAccessError:
    defaults_group = None
##-- end defaults

##-- pip/py
try:
    data_toml.project
    data_toml.tool.doot.pip
    from doot.builders import pip_install as pip
    from doot.code import python as py_tasks
    pip_dirs = doot_dirs.extend(prefix="pip")
    pip_dirs.add_extra({"wheel" : pip_dirs.build / "wheel",
                        "sdist" : pip_dirs.build / "sdist"})

    pip_group = TaskGroup("pip_group",
                          *pip.build_tasks(pip_dirs),
                          pip.pip_requirements,
                          py_tasks.InitPyGlobber(pip_dirs),
                          py_tasks.PyLintTask(pip_dirs),
                          py_tasks.PyUnitTestGlob(pip_dirs),
                          )
except TomlAccessError:
    pip_group = None
##-- end pip/py

##-- jekyll
try:
    data_toml.tool.doot.jekyll
    from doot.builders import jekyll as j_build
    from doot.docs import jekyll as j_doc
    jekyll_config = pl.Path("jekyll.toml")
    jekyll_toml   = TomlAccess.load("jekyll.toml")
    jekyll_src    = pl.Path(jekyll_toml.or_get("docs/site").source())
    jekyll_dest   = pl.Path(jekyll_toml.or_get("build/jekyll").destination())

    jekyll_dirs = doot_dirs.extend(prefix="jekyll", _src=jekyll_src, _build=jekyll_dest)
    jekyll_dirs.add_extra({
        "posts"     : jekyll_dirs.src / "posts" ,
        "tags"      : jekyll_dirs.codegen / "tags",
        "tagsIndex" : jekyll_dirs.src / "tags" / "index.md",
    })
    jekyll_group = TaskGroup("jekyll_group",
                             j_build.task_jekyll_serve,
                             j_build.task_jekyll_build(jekyll_config),
                             j_build.task_jekyll_install(jekyll_config),
                             j_build.task_init_jekyll(jekyll_config, jekyll_dirs),
                             j_doc.GenPostTask(jekyll_dirs),
                             j_doc.GenTagsTask(jeykll_dirs),
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
    tex_dirs = doot_dirs(prefix="tex", _src="docs")
    latex_group = TaskGroup("latex_group",
                            latex.LatexMultiPass(tex_dirs,  [tex_dirs.src]),
                            latex.LatexFirstPass(tex_dirs,  [tex_dirs.src]),
                            latex.LatexSecondPass(tex_dirs, [tex_dirs.src]),
                            latex.BibtexBuildTask(tex_dirs, [tex_dirs.src]),
                            latex.BibtexConcatenateTask(tex_dirs),
                            latex.LatexCheck(tex_dirs, [tex_dirs.src]),
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
    sphinx_dirs  = doot_dirs.extend(prefix="sphinx")
    sphinx_dirs.add_extra({"html" : sphinx_dirs.build / "html" / "index.html"})
    sphinx_group = TaskGroup("sphinx_group",
                             sphinx.SphinxDocTask(sphinx_dirs),
                             sphinx.task_browse(sphinx_dirs),
                             )
except TomlAccessError:
    sphinx_group = None
##-- end sphinx

##-- gtags
try:
    data_toml.tool.doot.gtags
    from doot.data import gtags
    gtags_dirs = doot_dirs.extend(prefix="gtags")
    gtags_group = TaskGroup("gtags_group",
                            gtags.task_tags_init(gtags_dirs),
                            gtags.task_tags(gtags_dirs),
                            )
except TomlAccessError:
    gtags_group = None
##-- end gtags

##-- git
try:
    data_toml.tool.doot.git
    from doot.vcs import git_tasks
    vcs_dirs = doot_dirs.extend(prefix="vcs", _src=None)
    vcs_dirs.add_extra({ "visual" : doot_dirs.docs / "visual" })
    git_group = TaskGroup("git group",
                          git_tasks.GitLogTask(vcs_dirs),
                          git_tasks.GitLogAnalyseTask(vcs_dirs),
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

    cargo_dirs = door_dirs.extend("cargo")
    from doot.builders import cargo
    cargo_group = TaskGroup("cargo_group",
                            cargo.task_cargo_build(cargo_dirs, ("bin", bin_file)),
                            cargo.task_cargo_build(cargo_dirs, ("bin", bin_file), profile="release"),
                            cargo.task_cargo_mac_lib(cargo_dirs, package=data_toml.package.name),
                            cargo.task_cargo_install,
                            cargo.task_cargo_test(("bin", "bin_file")),
                            cargo.task_cargo_run,
                            cargo.task_cargo_doc,
                            cargo.task_cargo_clean,
                            cargo.task_cargo_check,
                            cargo.task_cargo_update,
                            cargo.task_rustup_show,
                            cargo.task_cargo_help,
                            cargo.task_cargo_debug(cargo_dirs, target=("bin", bin_file)),
                            cargo.task_cargo_version,
                            )
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
                             gradle.task_gradle_test,
                             gradle.task_gradle_list,
                             gradle.task_gradle_projects,
                             )
except TomlAccessError:
    gradle_group = None
##-- end gradle

##-- epub
try:
    data_toml.tool.doot.epub
    epub_dirs = doot_dirs.extend(prefix="epub", _src="docs/epub")
    from doot.builders import epub
    epub_group = TaskGroup("epub group",
                           epub.EbookNewTask(epub_dirs),
                           epub.EbookCompileTask(epub_dirs),
                           epub.EbookConvertTask(epub_dirs),
                           epub.EbookZipTask(epub_dirs),
                           epub.EbookManifestTask(epub_dirs),
                           epub.EbookSplitTask(epub_dirs),
                           epub.EbookRestructureTask(epub_dirs),
                           )
except TomlAccessError:
    epub_group = None
##-- end epub
