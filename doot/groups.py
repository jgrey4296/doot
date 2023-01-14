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

import doot
from doot.utils.task_group import TaskGroup
from doot.utils.toml_access import TomlAccessError, TomlAccess

from doot import project_init
from doot.errors import DootDirAbsent
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

__all__ = [ "defaults_group",
            "pip_group", "jekyll_group", "sphinx_group",
            "latex_group", "tags_group", "git_group",
            "cargo_group", "epub_group", "py_group",
           ]


##-- defaults
defaults_group = TaskGroup("defaults")
try:
    from doot.files import list_all
    for x in ["src", "data", "docs", "build", "temp", "codegen"]:
        try:
            defaults_group += list_all.task_list_target(x, getattr(doot.locs, x), doot.locs)
        except DootDirAbsent:
            pass

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.defaults.debug():
        print("To activate group, defaults needs: ", err)

##-- end defaults

##-- pip
pip_group = TaskGroup("pip group")
try:
    if not doot.default_py.exists():
        raise FileNotFoundError(doot.default_py)
    doot.config.tool.doot.group.pip

    pip_dirs = doot.locs.extend(name="pip", _docs=None)
    pip_dirs.update(wheel=pip_dirs.build / "wheel")

    from doot.builders import pip_tasks as pipper
    pip_group += pipper.IncrementVersion(dirs=pip_dirs)
    pip_group += pipper.PyBuild(dirs=pip_dirs)
    pip_group += pipper.PyInstall(dirs=pip_dirs)
    pip_group += pipper.PipReqs(dirs=pip_dirs)
    pip_group += pipper.VenvNew(dirs=pip_dirs)
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.pip.debug():
        print("To activate group pip needs: ", err)
##-- end pip

##-- py
py_group = TaskGroup("py group")
try:
    if not doot.default_py.exists():
        raise FileNotFoundError(doot.default_py)
    doot.config.tool.doot.group.python
    py_dirs = doot.locs.extend(name="py", docs=None)

    from doot.code import python as py_tasks
    py_group += py_tasks.InitPyGlobber(dirs=py_dirs)
    py_group += py_tasks.PyLintTask(dirs=py_dirs)
    py_group += py_tasks.PyUnitTestGlob(dirs=py_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.pip.debug():
        print("To activate group python needs: ", err)

##-- end py

##-- jekyll
jekyll_group = TaskGroup("jekyll_group")
try:
    doot.config.tool.doot.group.jekyll


    jekyll_dirs = doot.locs.extend(name="jekyll",
                                   _src=doot.locs.docs,
                                   _data=(doot.locs.data,),
                                   _codegen="_generated",
                                   _docs=None)
    jekyll_dirs.update({
        "posts"     : jekyll_dirs.src / "_drafts" ,
        "tags"      : jekyll_dirs.codegen / "_tags",
        "tagsIndex" : jekyll_dirs.data / "tags" / "index.md",
    })

    jekyll_group += project_init.JekyllInit(dirs=jekyll_dirs)
    from doot.builders import jekyll as j_build
    jekyll_group += j_build.JekyllBuild(dirs=jekyll_dirs)
    jekyll_group += j_build.task_jekyll_serve
    jekyll_group += j_build.task_jekyll_install()
    from doot.docs import jekyll as j_doc
    jekyll_group += j_doc.GenPostTask(dirs=jekyll_dirs)
    jekyll_group += j_doc.GenTagsTask(dirs=jekyll_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.jekyll.debug():
        print("To activate group, jekyll needs: ", err)

##-- end jekyll

##-- latex
latex_group = TaskGroup("latex_group")
try:
    doot.config.tool.doot.group.latex
    from doot.builders import latex
    tex_dirs = doot.locs.extend(name="latex", _src=doot.locs._docs, _docs=(doot.locs._docs,), _build=(doot.locs._build,))
    latex_group += latex.LatexMultiPass(dirs=tex_dirs,  roots=[tex_dirs.src])
    latex_group += latex.LatexFirstPass(dirs=tex_dirs,  roots=[tex_dirs.src])
    latex_group += latex.LatexSecondPass(dirs=tex_dirs, roots=[tex_dirs.src])
    latex_group += latex.BibtexBuildPass(dirs=tex_dirs, roots=[tex_dirs.src])
    latex_group += latex.BibtexConcatenateSweep(dirs=tex_dirs, roots=[tex_dirs.src])
    latex_group += latex.task_latex_install()
    latex_group += latex.task_latex_requirements()
    latex_group += latex.task_latex_rebuild

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.latex.debug():
        print("To activate group, latex needs: ", err)
##-- end latex

##-- sphinx
sphinx_group = TaskGroup("sphinx_group")
try:
    doot.config.tool.doot.group.sphinx
    from doot.builders import sphinx
    sphinx_dirs  = doot.locs.extend(name="sphinx",
                                    _src=doot.locs.docs,
                                    _docs=(doot.locs.docs,))
    sphinx_dirs.update({"html" : sphinx_dirs.build / "html" / "index.html"})

    sphinx_group += sphinx.SphinxDocTask(dirs=sphinx_dirs)
    sphinx_group += sphinx.task_browse(sphinx_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.sphinx.debug():
        print("To activate group, sphinx needs: ", err)
##-- end sphinx

##-- tags
tags_group = TaskGroup("tags_group")
try:
    doot.config.tool.doot.group.tags
    from doot.data import taggers
    gtags_dirs = doot.locs.extend(name="tags",
                                  _build=None,
                                  _temp=None,
                                  _docs=None)

    tags_group += taggers.task_tags_init(gtags_dirs)
    tags_group += taggers.task_tags(gtags_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.tags.debug():
        print("To activate group, tags needs: ", err)
##-- end tags

##-- git
git_group = TaskGroup("git group")
try:
    doot.config.tool.doot.group.git
    from doot.vcs import git_tasks
    vcs_dirs = doot.locs.extend(name="vcs", _src=None, _docs=None, _temp=None)
    vcs_dirs.update({ "visual" : doot.locs.docs / "visual" })

    git_group += git_tasks.GitLogTask(dirs=vcs_dirs)
    git_group += git_tasks.GitLogAnalyseTask(dirs=vcs_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.git.debug():
        print("To activate group, git needs: ", err)

##-- end git

##-- cargo
cargo_group = TaskGroup("cargo_group")
try:
    doot.config.tool.doot.group.cargo
    doot.config.package
    # TODO swap this with a load of cargo file
    bin_file = doot.config.package.name
    try:
        bin_file = doot.config.bin[0].name
    except TomlAccessError:
        pass

    cargo_dirs = door_dirs.extend("cargo")
    from doot.builders import cargo

    cargo_group += cargo.task_cargo_build(cargo_dirs, ("bin", bin_file))
    cargo_group += cargo.task_cargo_build(cargo_dirs, ("bin", bin_file), profile="release")
    cargo_group += cargo.task_cargo_mac_lib(cargo_dirs, package=doot.config.package.name)
    cargo_group += cargo.task_cargo_install
    cargo_group += cargo.task_cargo_test(("bin", "bin_file"))
    cargo_group += cargo.task_cargo_run
    cargo_group += cargo.task_cargo_doc
    cargo_group += cargo.task_cargo_clean
    cargo_group += cargo.task_cargo_check
    cargo_group += cargo.task_cargo_update
    cargo_group += cargo.task_rustup_show
    cargo_group += cargo.task_cargo_help
    cargo_group += cargo.task_cargo_debug(cargo_dirs, target=("bin", bin_file))
    cargo_group += cargo.task_cargo_version

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.cargo.debug():
        print("To activate group, cargo needs: ", err)

##-- end cargo

##-- gradle
gradle_group = TaskGroup("gradle_group")
try:
    doot.config.tool.doot.group.gradle
    from doot.builders import gradle

    gradle_group += gradle.task_gradle_run
    gradle_group += gradle.task_gradle_build
    gradle_group += gradle.task_gradle.assemble
    gradle_group += gradle.task_gradle.check
    gradle_group += gradle.task_gradle_clean
    gradle_group += gradle.task_gradle_doc
    gradle_group += gradle.task_gradle_logging
    gradle_group += gradle.task_gradle_version
    gradle_group += gradle.task_gradle_test
    gradle_group += gradle.task_gradle_list
    gradle_group += gradle.task_gradle_projects

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.gradle.debug():
        print("To activate group, gradle needs: ", err)

##-- end gradle

##-- epub
epub_group = TaskGroup("epub group")
try:
    doot.config.tool.doot.group.epub
    epub_dirs = doot.locs.extend(name="epub", _src="docs/epub")
    from doot.builders import epub
    epub_group += epub.EbookNewTask(dirs=epub_dirs)
    epub_group += epub.EbookCompileTask(dirs=epub_dirs)
    epub_group += epub.EbookConvertTask(dirs=epub_dirs)
    epub_group += epub.EbookZipTask(dirs=epub_dirs)
    epub_group += epub.EbookManifestTask(dirs=epub_dirs)
    epub_group += epub.EbookSplitTask(dirs=epub_dirs)
    epub_group += epub.EbookRestructureTask(dirs=epub_dirs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.or_get(False).tool.doot.group.epub.debug():
        print("To activate group, epub needs: ", err)

##-- end epub
