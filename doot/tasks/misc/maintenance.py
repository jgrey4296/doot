# -*- mode:doot; -*-
#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import shutil
import time
import types
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
from doit.exceptions import TaskError
from doot import globber, tasker
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.commander import CommanderMixin
from doot.tasker import DootTasker

mbsync  = shutil.which("mbsync")
rustup  = shutil.which("rustup")
cargo   = shutil.which("cargo")
tlmgr   = shutil.which("tlmgr")
cabal   = shutil.which("cabal")
doom    = shutil.which("doom")
brew    = shutil.which("brew")
conda   = shutil.which("conda")
crontab = shutil.which("crontab")
git     = shutil.which("git")

class CheckMail(DootTasker, CommanderMixin):

    def __init__(self, name="mail::check", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
                    "actions": [
                        self.make_cmd(mbsync, "-a"),
                     ],
        })
        return task

class MaintainFull(DootTasker, CommanderMixin, FilerMixin):
    """
    Run all maintain tasks combined
    """

    def __init__(self, name="maintain", locs=None):
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
                (self.log, ["Full Maintenance", logmod.INFO]),
            ],
            "task_dep" : [  "_maintain::cron", "_maintain::git",  "_maintain::brew", "_maintain::conda", "_maintain::rust", "_maintain::haskell", "_maintain::doom",  "_maintain::latex"],
        })
        return task

class RustMaintain(DootTasker, CommanderMixin, FilerMixin):

    def __init__(self, name="_maintain::rust", locs=None):
        super().__init__(name, locs)
        locs.ensure("maintain", task=name)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                self.make_cmd(rustup, "--version", save="rustup"),
                self.make_cmd(cargo, "--version", save="cargo"),
                (self.write_to, [self.locs.maintain / "rust.versions", ["rustup", "cargo"]]),
            ],
        })
        return task

    def task_detail(self, task):
        if not bool(rustup):
            logging.warning("No Rustup found")
            return None

        task.update({
            "actions" : [
                (self.log, ["Updating Rust", logmod.INFO]),
                self.make_cmd(rustup, "update", save="rustup"),
                (self.write_to, [self.locs.maintain / "rust.backup", "rustup"]),
            ],
        })
        return task

class LatexMaintain(DootTasker, CommanderMixin, FilerMixin):

    def __init__(self, name="_maintain::latex", locs=None):
        super().__init__(name, locs)
        locs.ensure("maintain", task=name)

    def setup_detail(self, task):
        if not bool(tlmgr):
            logging.warning("No tlmgr found")
            return None

        task.update({
            "actions" : [
                # Backup tex packages
                self.make_cmd(tlmgr, "info", "--only-installed", save="tex"),
                (self.write_to, [self.locs.maintain / "tex.versions", ["tex"]]),

            ],
        })
        return task

    def task_detail(self, task):
        if not bool(tlmgr):
            logging.warning("No tlmgr found")
            return None

        task.update({
            "actions" : [
                (self.log, ["Updating Latex", logmod.INFO]),
                self.make_cmd(tlmgr, "update", "--all", save="update"),
                (self.write_to, [self.locs.maintain / "tex.log",  "update"])
            ],
        })
        return task

class HaskellMaintain(DootTasker, CommanderMixin, FilerMixin):

    def __init__(self, name="_maintain::haskell", locs=None):
        super().__init__(name, locs)
        locs.ensure("maintain", task=name)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                self.make_cmd(cabal, "--version", save="cabal"),
                self.make_cmd(cabal, "list", "--installed", save="cabal.installed"),
                (self.write_to, [self.locs.maintain / "cabal.version", ["cabal", "cabal.installed"]]),
            ],
        })
        return task

    def task_detail(self, task):
        if not bool(cabal):
            logging.warning("No Cabal found")
            return None

        task.update({
            "actions" : [
                (self.log, ["Updating Cabal", logmod.INFO]),
                self.make_cmd(cabal, "update", save="cabal"),
                (self.write_to, [self.locs.maintain / "cabal.backup", "cabal"]),
            ],
        })
        return task

class DoomMaintain(DootTasker, CommanderMixin, FilerMixin):

    def __init__(self, name="_maintain::doom", locs=None):
        super().__init__(name, locs)
        locs.ensure("maintain", task=name)

    def setup_detail(self, task):
        if doom is None:
            return None

        task.update({
                    "actions": [
                        self.make_cmd(doom, "version", save="doom"),
                        self.make_cmd(doom, "info", save="doom.info"),
                        (self.write_to, [self.locs.maintain / "doom.versions", ["doom", "doom.info"]]),
                    ],
        })
        return task

    def task_detail(self, task):
        if doom is None:
            return task

        task.update({
            "actions" : [
                (self.log, ["Updating Doom", logmod.INFO]),
                self.make_cmd(doom, "upgrade", "-!", "-v", save="upgrade"),
                self.make_cmd(doom, "sync", "-v", save="sync"),
                (self.write_to, [self.locs.maintain / "doom.backup", ["upgrade", "sync"]]),
            ],
        })
        return task

class BrewMaintain(DootTasker, CommanderMixin, FilerMixin):

    def __init__(self, name="_maintain::brew", locs=None):
        super().__init__(name, locs)
        locs.ensure("maintain", task=name)

    def setup_detail(self, task):
        task.update({
            "actions": [
                self.make_cmd(brew, "--version", save="brew_version"),
                self.make_cmd(brew, "list", "--version", save="installed_versions"),
                (self.write_to, [self.locs.maintain / "brew.versions", ["brew_version", "installed_versions"]]),
            ]
        })
        return task

    def task_detail(self, task):
        if not bool(brew):
            logging.warning("No Brew found")
            return None

        task.update({
            "actions" : [
                (self.log, ["Updating Homebrew", logmod.INFO]),
                self.make_cmd(brew, "cleanup", save="cleanup"),
                self.make_cmd(brew, "update",  save="update"),
                self.make_cmd(brew, "upgrade", save="upgrade"),
                (self.append_to, [self.locs.maintain / "brew.log", ["cleanup", "update", "upgrade"]]),
            ],
        })
        return task

class CondaMaintain(DootTasker,CommanderMixin, FilerMixin):

    def __init__(self, name="_maintain::conda", locs=None):
        super().__init__(name, locs)
        locs.ensure("maintain", task=name)

    def setup_detail(self, task):
        if conda is None:
            return None

        task.update({
                    "actions": [
                        self.make_cmd(conda, "--version", save="conda"),
                        (self.write_to, [self.locs.maintain / "conda.versions", ["conda"]]),
                     ],
        })
        return task

    def task_detail(self, task):
        if conda is None:
            return task

        task.update({
            "actions" : [
                (self.log, ["Updating Conda Environments", logmod.INFO]),
                self._maintain,
            ],
        })
        return task

    def _maintain(self):
        for env in self.locs.conda_envs.glob("*.yaml"):
            name = env.stem
            update_cmd = self.in_conda(name, conda, "update", "--all", "-y")
            export_cmd = self.in_conda(name, conda, "env", "export", "--from-history")
            update_cmd.execute()
            export_cmd.execute()
            env.write_text(update_cmd.out + "\n--------------------\n" + export_cmd.out)

class CronMaintain(DootTasker, CommanderMixin, FilerMixin):

    def __init__(self, name="_maintain::cron", locs=None):
        super().__init__(name, locs)
        locs.ensure("maintain", task=name)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                # Backup cron
                self.make_cmd(crontab, "-l", save="cron"),
                (self.write_to, [self.locs.maintain / "cron.backup", ["cron"]]),
            ],
        })
        return task

    def task_detail(self, task):
        if not bool(crontab):
            logging.warning("No cron found")
            return None

        task.update({
            "actions" : [
                (self.log, ["Cron Maintenance", logmod.INFO]),
            ],
        })
        return task

class GitMaintain(DelayedMixin, globber.DootEagerGlobber, FilerMixin, CommanderMixin):

    def __init__(self, name="_maintain::git", locs=None, roots=None):
        super().__init__(name, locs, roots or [locs.git_libs.resolve(), locs.github.resolve()], rec=True)
        locs.ensure("maintain", task=name)
        self.output = self.locs.maintain / "git.version"

    def filter(self, fpath):
        if not fpath.is_dir():
            return self.control.discard
        if (fpath / ".doot_ignore").exists():
            return self.control.reject
        if fpath.is_symlink():
            return self.control.reject

        match self.make_cmd(git, "rev-parse", "--is-inside-work-tree", cwd=fpath).execute():
            case TaskError():
                return self.control.discard
            case _:
                return self.control.keep

    def setup_detail(self, task):
        task.update({
            "actions" : [
                self.make_cmd(git, "--version", save="git"),
                (self.write_to, [self.output, "git"]),
            ],
        })
        return task

    def task_detail(self, task):
        if not bool(git):
            logging.warning("No git found")
            return None

        task.update({
            "actions" : [
                (self.log, ["Recording Git Repo Urls", logmod.INFO]),
            ],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                (self.log, [f"Getting Repo: {fpath}", logmod.INFO]),
                self.make_cmd(git, "config", "--get-regexp", "url", cwd=fpath, save="urls"),
                (self.append_to, [self.output, "urls"]),
            ],
        })
        return task
