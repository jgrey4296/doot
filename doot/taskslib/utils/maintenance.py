# -*- mode:doot; -*-
#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot
from doot import tasker, globber, task_mixins
from doot.tasker import DootTasker
from doit.exceptions import TaskError

class CheckMail(tasker.DootTasker, task_mixins.CommanderMixin):

    def __init__(self, name="mail::check", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
                    "actions": [
                        self.cmd(["/usr/local/bin/mbsync", "-a"]),
                     ],
        })
        return task

class MaintainFull(task_mixins.FilerMixin, DootTasker, task_mixins.CommanderMixin):
    """
    Run all maintain tasks combined
    """

    def __init__(self, name="maintance", locs=None):
        super().__init__(name, locs)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                (self.mkdirs, [self.locs.maintain]),
            ]
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
            ],
            "task_dep" : ["maintain::*"],
        })
        return task

class RustMaintain(DootTasker):

    def __init__(self, name="maintain::cargo", locs=None):
        super().__init__(name, locs)
        assert(locs.maintain)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                self.cmd(["rustup", "--version"], save="rustup"),
                self.cmd(["cargo", "--version"], save="cargo"),
                (self.write_to, [self.locs.maintain / "rust.versions", ["rustup", "cargo"]]),
            ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.cmd(["rustup", "update"], save="rustup"),
                (self.write_to, [self.locs.maintain / "rust.backup", "rustup"]),
            ],
        })
        return task

class LatexMaintain(DootTasker):

    def __init__(self, name="maintain::latex", locs=None):
        super().__init__(name, locs)
        assert(locs.maintain)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                # Backup tex packages
                self.cmd(["tlmgr", "info", "--only-installed"], save="tex"),
                (self.write_to, [self.locs.maintain / "tex.versions", ["tex"]]),

            ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.cmd(["tlmgr", "update", "--all"], save="update"),
                (self.write_to, [self.locs.maintain / "tex.log",  "update"])
            ],
        })
        return task

class CabalMaintain(DootTasker):

    def __init__(self, name="maintenace::cabal", locs=None):
        super().__init__(name, locs)
        assert(locs.maintain)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                self.cmd(["cabal", "--version"], save="cabal"),
                self.cmd(["cabal", "list", "--installed"], save="cabal.installed"),
                (self.write_to, [self.locs.maintain / "cabal.version", ["cabal", "cabal.installed"]]),
            ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.cmd(["cabal", "update"], save="cabal"),
                (self.write_to, [self.locs.maintain / "cabal.backup", "cabal"]),
            ],
        })
        return task

class DoomMaintain(DootTasker):

    def __init__(self, name="maintain::doom", locs=None):
        super().__init__(name, locs)
        assert(locs.maintain)

    def setup_detail(self, task):
        task.update({
                    "actions": [
                        self.cmd(["doom", "version"], save="doom"),
                        self.cmd(["doom", "info"], save="doom.info"),
                        (self.write_to, [self.locs.maintain / "doom.versions", ["doom", "doom.info"]]),
                    ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [ self.cmd(["doom", "upgrade", "-!", "-v"], save="upgrade"),
                          self.cmd(["doom", "sync", "-v"], save="sync"),
                          (self.write_to, [self.locs.maintain / "doom.backup", ["upgrade", "sync"]]),
                     ],
        })
        return task

class BrewMaintain(DootTasker):

    def __init__(self, name="maintain::brew", locs=None):
        super().__init__(name, locs)
        assert(locs.maintain)

    def setup_detail(self, task):
        task.update({
            "actions": [
                self.cmd(["brew", "--version"], save="brew_version"),
                self.cmd(["brew", "list", "--version"], save="installed_versions"),
                (self.write_to, [self.locs.maintain / "brew.versions", ["brew_version", "installed_versions"]]),
            ]
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                # Brew cleanup
                self.cmd(["brew", "cleanup"], save="cleanup"),
                self.cmd(["brew", "update"],  save="update"),
                self.cmd(["brew", "upgrade"], save="upgrade"),
                (self.append_to, [self.maintain / "brew.log", ["cleanup", "update", "upgrade"]]),
            ],
        })
        return task

class CondaMaintain(DootTasker):

    def __init__(self, name="maintain::conda", locs=None):
        super().__init__(name, locs)
        assert(locs.maintain)

    def setup_detail(self, task):
        task.update({
                    "actions": [
                        self.cmd(["conda", "--version"], save="conda"),
                        (self.write_to, [self.locs.maintain / "conda.versions", ["conda"]]),
                     ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.maintain,
            ],
        })
        return task

    def maintain(self):
        for env in self.locs.conda_envs.glob("*.yaml"):
            name = env.stem
            update_cmd = self.in_conda(name, "conda", "update", "--all", "-y")
            export_cmd = self.in_conda(name, "conda", "env", "export", "--from-history")
            update_cmd.execute()
            export_cmd.execute()
            env.write_text(update_cmd.out + "\n--------------------\n" + export_cmd.out)

class CronMaintain(DootTasker):

    def __init__(self, name="maintain::cron", locs=None):
        super().__init__(name, locs)
        assert(locs.maintain)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                # Backup cron
                self.cmd(["crontab" "-l"], save="cron"),
                (self.write_to, [self.locs.maintain / "cron.backup", ["cron"]]),
            ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [],
        })
        return task
class GitMaintain(globber.LazyGlobMixin, globber.DirGlobMixin, globber.DootEagerGlobber):

    def __init__(self, name="maintain::git", locs=None, roots=None):
        super().__init__(name, locs, roots or [locs.github], rec=True)
        assert(locs.maintain)

    def filter(self, fpath):
        try:
            self.cmd(["git", "rev-parse", "--is-inside-work-tree"]).execute()
            return self.control.keep
        except TaskError:
            return self.control.discard

    def setup_detail(self, task):
        task.update({
            "actions" : [
                self.cmd(["git", "--version"], save="git"),
                (self.write_to, [self.locs.maintain / "git.version", "git"]),
            ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.get_repo_urls,
            ],
        })
        return task

    def get_repo_urls(self):
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        results = []
        for name, fpath in globbed:
            cmd = self.cmd(["git", "config", "--get-regexp", "url"], save="urls")
            cmd.execute()
            results += cmd.result.split("\n")

        (self.locs.maintain / "git.urls").write_text("\n".join(sorted(results)))
