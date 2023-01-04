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
    "latex_group", "gtags_group", "git_group",
    "cargo_group", "epub_group",
]

announce_group_fails = doot.config.or_get(False).tool.doot.announce_groups()
##-- defaults
try:
    from doot.files import listall
    doot.locs.add_extra({ "visual" : doot.locs.docs / "visual" })

    defaults_group = TaskGroup("defaults")
    for x in ["src", "data", "docs", "build", "temp", "codegen"]:
        try:
            defaults_group += listall.task_list_target(x,     getattr(doot.locs, x),      doot.locs)
        except DootDirAbsent:
            pass

except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    defaults_group = None
    if announce_group_fails:
        print("To activate group, defaults needs: ", err)
##-- end defaults

##-- pip/py
try:
    if not doot.default_py.exists():
        raise FileNotFoundError(doot.default_py)
    doot.config.tool.doot.pip
    from doot.builders import pip_install as pip
    from doot.code import python as py_tasks
    pip_dirs = doot.locs.extend(prefix="pip")
    pip_dirs.add_extra({"wheel" : pip_dirs.build / "wheel",
                        "sdist" : pip_dirs.build / "sdist"})

    pip_group = TaskGroup("pip_group",
                          *pip.build_tasks(pip_dirs),
                          pip.pip_requirements,
                          py_tasks.InitPyGlobber(pip_dirs),
                          py_tasks.PyLintTask(pip_dirs),
                          py_tasks.PyUnitTestGlob(pip_dirs),
                          )
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    pip_group = None
    if announce_group_fails:
        print("To activate group pip needs: ", err)

##-- end pip/py

##-- jekyll
try:
    doot.config.tool.doot.jekyll
    from doot.builders import jekyll as j_build
    from doot.docs import jekyll as j_doc
    jekyll_config = pl.Path("jekyll.toml")
    jekyll_toml   = TomlAccess.load("jekyll.toml")
    jekyll_src    = pl.Path(jekyll_toml.or_get("docs/site").source())
    jekyll_dest   = pl.Path(jekyll_toml.or_get("build/jekyll").destination())

    jekyll_dirs = doot.locs.extend(prefix="jekyll", _src=jekyll_src, _build=jekyll_dest)
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
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    jekyll_group = None
    if announce_group_fails:
        print("To activate group, jekyll needs: ", err)

##-- end jekyll

##-- latex
try:
    doot.config.tool.doot.tex
    from doot.builders import latex
    tex_dirs = doot.locs(prefix="tex", _src="docs")
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
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    latex_group = None
    if announce_group_fails:
        print("To activate group, latex needs: ", err)
##-- end latex

##-- sphinx
try:
    doot.config.tool.doot.sphinx
    from doot.builders import sphinx
    sphinx_dirs  = doot.locs.extend(prefix="sphinx")
    sphinx_dirs.add_extra({"html" : sphinx_dirs.build / "html" / "index.html"})
    sphinx_group = TaskGroup("sphinx_group",
                             sphinx.SphinxDocTask(sphinx_dirs),
                             sphinx.task_browse(sphinx_dirs),
                             )
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    sphinx_group = None
    if announce_group_fails:
        print("To activate group, sphinx needs: ", err)
##-- end sphinx

##-- gtags
try:
    doot.config.tool.doot.gtags
    from doot.data import gtags
    gtags_dirs = doot.locs.extend(prefix="gtags")
    gtags_group = TaskGroup("gtags_group",
                            gtags.task_tags_init(gtags_dirs),
                            gtags.task_tags(gtags_dirs),
                            )
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    gtags_group = None
    if announce_group_fails:
        print("To activate group, gtags needs: ", err)
##-- end gtags

##-- git
try:
    doot.config.tool.doot.git
    from doot.vcs import git_tasks
    vcs_dirs = doot.locs.extend(prefix="vcs", _src=None)
    vcs_dirs.add_extra({ "visual" : doot.locs.docs / "visual" })
    git_group = TaskGroup("git group",
                          git_tasks.GitLogTask(vcs_dirs),
                          git_tasks.GitLogAnalyseTask(vcs_dirs),
                          )
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    git_group = None
    if announce_group_fails:
        print("To activate group, git needs: ", err)

##-- end git

##-- cargo
try:
    doot.config.tool.doot.cargo
    doot.config.package
    # TODO swap this with a load of cargo file
    bin_file = doot.config.package.name
    try:
        bin_file = doot.config.bin[0].name
    except TomlAccessError:
        pass

    cargo_dirs = door_dirs.extend("cargo")
    from doot.builders import cargo
    cargo_group = TaskGroup("cargo_group",
                            cargo.task_cargo_build(cargo_dirs, ("bin", bin_file)),
                            cargo.task_cargo_build(cargo_dirs, ("bin", bin_file), profile="release"),
                            cargo.task_cargo_mac_lib(cargo_dirs, package=doot.config.package.name),
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
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    cargo_group = None
    if announce_group_fails:
        print("To activate group, cargo needs: ", err)

##-- end cargo

##-- gradle
except TomlAccessError:
    doot.config.tool.doot.gradle
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
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    gradle_group = None
    if announce_group_fails:
        print("To activate group, gradle needs: ", err)

##-- end gradle

##-- epub
try:
    doot.config.tool.doot.epub
    epub_dirs = doot.locs.extend(prefix="epub", _src="docs/epub")
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
except (TomlAccessError, DootDirAbsent, FileNotFoundError) as err:
    epub_group = None
    if announce_group_fails:
        print("To activate group, epub needs: ", err)

##-- end epub
