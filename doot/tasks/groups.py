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

from tomler import TomlAccessError
import doot
from doot.task_group import TaskGroup

from doot.tasks import project_init
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
            "maintain_group", "hashing_group"
           ]

##-- defaults

defaults_group = TaskGroup("defaults", as_creator=False)
try:
    from doot.tasks.files import listing

    defaults_group += listing.FileListings(locs=doot.locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.defaults.debug():
        print("To activate group, defaults needs: ", err)

##-- end defaults

##-- pip
pip_group = TaskGroup("pip group")
try:
    if not doot.default_py.exists():
        raise FileNotFoundError(doot.default_py)
    doot.config.tool.doot.group.pip

    wheel_loc = doot.config.on_fail("build/wheel").tool.doot.group.pip.wheel()
    pip_locs = doot.locs.extend(name="pip", _docs=None, wheel=wheel_loc)

    from doot.tasks.builders import pip_tasks as pipper
    pip_group += pipper.IncrementVersion(locs=pip_locs)
    pip_group += pipper.PipBuild(locs=pip_locs)
    pip_group += pipper.PipInstall(locs=pip_locs)
    pip_group += pipper.PipReqs(locs=pip_locs)
    pip_group += pipper.VenvNew(locs=pip_locs)
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.pip.debug():
        print("To activate group pip needs: ", err)
##-- end pip

##-- py
py_group = TaskGroup("py group")
try:
    if not doot.default_py.exists():
        raise FileNotFoundError(doot.default_py)
    doot.config.tool.doot.group.python
    py_locs = doot.locs.extend(name="py", docs=None)

    from doot.tasks.code import python as py_tasks
    py_group += py_tasks.InitPyGlobber(locs=py_locs)
    py_group += py_tasks.PyLintTask(locs=py_locs)
    py_group += py_tasks.PyUnitTestGlob(locs=py_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.python.debug():
        print("To activate group python needs: ", err)

##-- end py

##-- jekyll
jekyll_group = TaskGroup("jekyll_group")
try:
    doot.config.tool.doot.group.jekyll

    jekyll_src = doot.config.on_fail(doot.locs.docs).tool.doot.group.jekyll.src()
    jekyll_data = doot.config.on_fail([doot.locs.data]).tool.doot.group.jekyll.data()
    jekyll_codegen = doot.config.on_fail("_generated").tool.doot.group.jekyll.codegen()

    jekyll_locs = doot.locs.extend(name="jekyll",
                                   src=jekyll_src,
                                   data=jekyll_data,
                                   codegen=jekyll_codegen,
                                   docs=None)
    jekyll_locs.update({
        "posts"     : jekyll_locs.src     / "_drafts" ,
        "tags"      : jekyll_locs.codegen / "_tags",
        "tagsIndex" : jekyll_locs.data    / "tags" / "index.md",
    })

    jekyll_group += project_init.JekyllInit(locs=jekyll_locs)
    from doot.tasks.builders import jekyll as j_build
    jekyll_group += j_build.JekyllBuild(locs=jekyll_locs)
    jekyll_group += j_build.task_jekyll_serve
    jekyll_group += j_build.task_jekyll_install()
    from doot.tasks.docs import jekyll as j_doc
    jekyll_group += j_doc.GenPostTask(locs=jekyll_locs)
    jekyll_group += j_doc.GenTagsTask(locs=jekyll_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.jekyll.debug():
        print("To activate group, jekyll needs: ", err)

##-- end jekyll

##-- latex
latex_group = TaskGroup("latex_group")
try:
    doot.config.tool.doot.group.latex
    from doot.tasks.builders import latex

    latex_src = doot.config.on_fail(doot.locs.docs).tool.doot.group.latex.src()
    latex_docs = doot.config.on_fail([doot.locs.docs]).tool.doot.group.latex.docs()
    latex_build = doot.config.on_fail([doot.locs.build]).tool.doot.group.latex.build()

    tex_locs = doot.locs.extend(name="latex", src=latex_src, docs=latex_docs, build=latex_build)
    latex_group += latex.LatexMultiPass(locs=tex_locs,  roots=[tex_locs.src])
    latex_group += latex.LatexFirstPass(locs=tex_locs,  roots=[tex_locs.src])
    latex_group += latex.LatexSecondPass(locs=tex_locs, roots=[tex_locs.src])
    latex_group += latex.BibtexBuildPass(locs=tex_locs, roots=[tex_locs.src])
    latex_group += latex.BibtexConcatenateSweep(locs=tex_locs, roots=[tex_locs.src])
    latex_group += latex.task_latex_install()
    latex_group += latex.task_latex_requirements()
    latex_group += latex.task_latex_rebuild

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.latex.debug():
        print("To activate group, latex needs: ", err)
##-- end latex

##-- sphinx
sphinx_group = TaskGroup("sphinx_group")
try:
    doot.config.tool.doot.group.sphinx
    from doot.tasks.builders import sphinx

    sphinx_src  = doot.config.on_fail(doot.locs.docs).tool.doot.group.sphinx.src()
    sphinx_docs = doot.config.on_fail([doot.locs.docs]).tool.doot.group.sphinx.docs()

    sphinx_locs  = doot.locs.extend(name="sphinx",
                                    src=sphinx_src,
                                    docs=sphinx_locs)
    sphinx_locs.update({"html" : sphinx_locs.build / "html" / "index.html"})

    sphinx_group += sphinx.SphinxDocTask(locs=sphinx_locs)
    sphinx_group += sphinx.task_browse(sphinx_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.sphinx.debug():
        print("To activate group, sphinx needs: ", err)
##-- end sphinx

##-- tags
tags_group = TaskGroup("tags_group")
try:
    doot.config.tool.doot.group.tags
    from doot.tasks.data import taggers
    gtags_locs = doot.locs.extend(name="tags",
                                  build=None,
                                  temp=None,
                                  docs=None)

    tags_group += taggers.task_tags_init(gtags_locs)
    tags_group += taggers.task_tags(gtags_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.tags.debug():
        print("To activate group, tags needs: ", err)
##-- end tags

##-- git
git_group = TaskGroup("git group")
try:
    doot.config.tool.doot.group.git
    from doot.tasks.vcs import git_tasks

    vcs_visual = doot.config.on_fail(doot.locs.docs / "visual").tool.doot.group.git.visual()

    vcs_locs = doot.locs.extend(name="vcs", src=None, docs=None, temp=None, visual=vcs_visual)

    git_group += git_tasks.GitLogTask(locs=vcs_locs)
    git_group += git_tasks.GitLogAnalyseTask(locs=vcs_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.git.debug():
        print("To activate group, git needs: ", err)

##-- end git

##-- cargo
cargo_group = TaskGroup("cargo_group")
try:
    doot.config.tool.doot.group.cargo

    from doot.tasks.builders import cargo
    cargo_locs = doot.locs.extend(name="cargo",
                                  build=cargo.build_path)

    cargo_group += cargo.CargoBuild(locs=cargo_locs)
    cargo_group += cargo.CargoInstall(locs=cargo_locs)
    cargo_group += cargo.CargoTest(locs=cargo_locs)
    cargo_group += cargo.CargoDocs(locs=cargo_locs)
    cargo_group += cargo.CargoRun(locs=cargo_locs)
    cargo_group += cargo.CargoClean(locs=cargo_locs)
    cargo_group += cargo.CargoCheck(locs=cargo_locs)
    cargo_group += cargo.CargoUpdate(locs=cargo_locs)
    cargo_group += cargo.CargoDebug(locs=cargo_locs)
    cargo_group += cargo.task_cargo_report
    cargo_group += cargo.task_cargo_version

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.cargo.debug():
        print("To activate group, cargo needs: ", err)

##-- end cargo

##-- gradle
gradle_group = TaskGroup("gradle_group")
try:
    doot.config.tool.doot.group.gradle
    from doot.tasks.builders import gradle

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
    if doot.config.on_fail(False, bool).tool.doot.group.gradle.debug():
        print("To activate group, gradle needs: ", err)

##-- end gradle

##-- epub
epub_group = TaskGroup("epub group")
try:
    doot.config.tool.doot.group.epub
    epub_src = doot.config.on_fail("docs/epub").tool.doot.group.epub.src()
    epub_build = doot.config.on_fail(["build"]).tool.doot.group.epub.build()

    epub_locs = doot.locs.extend(name="epub", src=epub_src, build=epub_build)
    from doot.tasks.builders import epub
    epub_group += epub.EbookNewTask(locs=epub_locs)
    epub_group += epub.EbookCompileTask(locs=epub_locs)
    epub_group += epub.EbookConvertTask(locs=epub_locs)
    epub_group += epub.EbookZipTask(locs=epub_locs)
    epub_group += epub.EbookManifestTask(locs=epub_locs)
    epub_group += epub.EbookSplitTask(locs=epub_locs)
    epub_group += epub.EbookRestructureTask(locs=epub_locs)
    epub_group += epub.EbookNewPandoc(locs=epub_locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.epub.debug():
        print("To activate group, epub needs: ", err)

##-- end epub

##-- maintain
maintain_group = TaskGroup("Maintain Group")
try:
    doot.config.tool.doot.group.maintain
    from doot.tasks.utils import maintenance as maintain
    maintain_group += maintain.CheckMail(locs=doot.locs)
    maintain_group += maintain.MaintainFull(locs=doot.locs)
    maintain_group += maintain.RustMaintain(locs=doot.locs)
    maintain_group += maintain.LatexMaintain(locs=doot.locs)
    maintain_group += maintain.CabalMaintain(locs=doot.locs)
    maintain_group += maintain.DoomMaintain(locs=doot.locs)
    maintain_group += maintain.BrewMaintain(locs=doot.locs)
    maintain_group += maintain.CondaMaintain(locs=doot.locs)
    maintain_group += maintain.CronMaintain(locs=doot.locs)
    maintain_group += maintain.GitMaintain(locs=doot.locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.maintain.debug():
        logging.debug("To activate group, epub needs: ", err)
##-- end maintain

##-- hashing
hashing_group = TaskGroup("Hashing")
try:
    doot.config.tool.doot.group.hashing
    from doot.tasks.files import hashing
    hashing_group += hashing.HashAllFiles(locs=doot.locs)
    hashing_group += hashing.GroupHashes(locs=doot.locs)
    hashing_group += hashing.RemoveMissingHashes(locs=doot.locs)
    hashing_group += hashing.DetectDuplicateHashes(locs=doot.locs)
    hashing_group += hashing.DeleteDuplicates(locs=doot.locs)
    hashing_group += hashing.RepeatDeletions(locs=doot.locs)

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    if doot.config.on_fail(False, bool).tool.doot.group.hashing.debug():
        logging.debug("To activate group, epub needs: ", err)
##-- end hashing
