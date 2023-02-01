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

plexp    = lambda x: pl.Path(x).expanduser()
lstplexp = lambda xs: [plexp(x) for x in xs]

cron_backup  = doot.config.on_fail("crontab.backup", str).tool.doot.maintenance.cron_backup()
cargo_backup  = doot.config.on_fail("cargo.backup", str).tool.doot.maintenance.cargo_backup()
cabal_backup = doot.config.on_fail("cabal.backup", str).tool.doot.maintenance.cabal_backup()
latex_backup = doot.config.on_fail("latex.backup", str).tool.doot.maintenance.latex_backup()
git_backup   = doot.config.on_fail("git_urls.backup", str).tool.doot.maintenance.git_backup()
brew_backup  = doot.config.on_fail("brew_installed.backup", str).tool.doot.maintenance.brew_backup()
doom_backup  = doot.config.on_fail("doom.backup", str).tool.doot.maintenance.doom_backup()

git_backup_watch = doot.config.on_fail(["~/github", "~/github/otherLibs", "~/github/inform", "~/github/python", "~/github/rust"], list).tool.doot.maintenance.git_watch(wrapper=lstplexp)
conda_envs_dir = doot.config.on_fail("~/.doom.d/terminal/conda_envs").tool.doot.maintenance.conda_envs(wrapper=plexp)

maintain_dir     = doot.config.on_fail("~/.doom.d/terminal/maintenance", str).tool.doot.maintenance.log(wrapper=plexp)

class CheckMail(tasker.DootTasker, task_mixins.CommanderMixin):

    def __init__(self, name="mail::check", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
                    "actions": [
                        self.cmd(["/usr/local/bin/mbsync" "-a"]),
                     ],
        })
        return task

class MaintainBackup(DootTasker, task_mixins.CommanderMixin):

    def __init__(self, name="maintenance::backup", dirs=None):
        super().__init__(name, dirs)

    def task_detail(self, task):
        task.update({
            "actions" : [
                # Backup cron
                self.cmd(["crontab" "-l"], save="cron"),
                # Backup git repo list
                #self.backup_git_urls, # -> git_urls
                # Backup brew installed list
                self.cmd(["brew list"], save="brew"),
                # Backup tex packages
                self.cmd(["tlmgr", "info", "--only-installed"], save="tex"),
                # Write as one log:
                (self.write_to, [maintain_dir / "total.backup", ["cron", "brew", "tex"]]),
            ],
        })
        return task

    def backup_git_urls(self):
        for root in git_backup_watch:
            for dirp in root.iterdir():
                pass

        # if git rev-parse --is-inside-work-tree > /dev/null 2> /dev/null
        # then
        # echo "$Dir" | sed 's/^.*github/---- github/' >> "$GIT_BKUP_TARGET"
        # Result=$( git config --local -l | awk '/url/ {print $0}' ) || "nothing"
        # echo "$Result" >> "$GIT_BKUP_TARGET"
        # echo "" >> "$GIT_BKUP_TARGET"
        # else
        # echo "---- $Dir" >> "$GIT_BKUP_TARGET"
        # echo "Not a repo" >> "$GIT_BKUP_TARGET"
        # echo "" >> "$GIT_BKUP_TARGET"
        # fi
        return { "git_urls" : [] }

class MaintainFull(DootTasker, task_mixins.CommanderMixin):
    """
    Run all maintenance tasks combined
    """

    def __init__(self, name="maintenance::full", dirs=None):
        super().__init__(name, dirs)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                (self.mkdirs, [maintain_dir]),
            ]
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
            ],
            "task_dep" : ["maintenance::conda", "maintance::brew"]
        })
        return task

class RustMaintain(DootTasker):

    def __init__(self, name="maintenance::cargo", dirs=None):
        super().__init__(name, dirs)

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.cmd(["rustup", "update"], save="rustup"),
                (self.write_to, [cargo_backup, "rustup"]),
            ],
        })
        return task

class LatexMaintain(DootTasker):

    def __init__(self, name="maintenance::latex", dirs=None):
        super().__init__(name, dirs)

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.cmd(["tlmgr", "update", "--all"], save="update"),
                (self.write_to, [maintain_dir / latex_backup,  "update"])
            ],
        })
        return task

class CabalMaintain(DootTasker):

    def __init__(self, name="maintenace::cabal", dirs=None):
        super().__init__(name, dirs)

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.cmd(["cabal", "update"], save="cabal"),
                (self.write_to, [maintain_dir / cabal_backup, "cabal"]),
            ],
        })
        return task

class DoomMaintain(DootTasker):

    def __init__(self, name="maintenance::doom", dirs=None):
        super().__init__(name, dirs)

    def setup_detail(self, task):
        task.update({
                    "actions": [ self.cmd(["doom", "--version"]) ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [ self.cmd(["doom", "upgrade", "-!", "-v"], save="upgrade"),
                          self.cmd(["doom", "sync", "-v"], save="sync"),
                          (self.write_to, [maintain_dir / doom_backup, ["upgrade", "sync"]]),
                     ],
        })
        return task

class BrewMaintain(DootTasker):

    def __init__(self, name="maintenance::brew", dirs=None):
        super().__init__(name, dirs)

    def setup_detail(self, task):
        task.update({
            "actions": [
                self.cmd(["brew", "--version"]),
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
                (self.append_to, [maintain_locs, ["cleanup", "update", "upgrade"]]),
            ],
        })
        return task

class CondaMaintain(DootTasker):

    def __init__(self, name="maintenance::conda", dirs=None):
        super().__init__(name, dirs)

    def setup_detail(self, task):
        task.update({
                    "actions": [ self.cmd(["conda", "--version"]),
                     ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.maintain,
                (self.write_to, [maintain_dir / conda_backup, "update"])
            ],
        })
        return task

    def maintain(self):
        for env in conda_envs_dir.glob("*.yaml"):
            name = env.stem
            update_cmd = self.in_conda(name, "conda", "update", "--all", "-y")
            export_cmd = self.in_conda(name, "conda", "env", "export", "--from-history")
            update_cmd.execute()
            export_cmd.execute()
            env.write_text(update_cmd.out + "\n--------------------\n" + export_cmd.out)
