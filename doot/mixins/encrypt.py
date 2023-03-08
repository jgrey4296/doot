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

import shutil

import doot
from doot.mixins.commander import CommanderMixin

gpg = shutil.which("gpg")
gpg_user = doot.config.encrypt.user_email

class EncryptMixin(CommanderMixin):
    """
    mixin for standard gnupg actions
    """

    def list_keys(self):
        cmd = self.cmd(gpg, "--list-keys")
        cmd.execute()
        print(cmd.result)

    def export_public(self, fpath, user=None, secret=False):
        """
        export a key to an ascii file
        """
        user = user or gpg_user
        if secret:
            cmd = self.cmd(gpg, "--armor", "--export-secret-keys",
                           "-o", fpath, gpg_user)
        else:
            cmd = self.cmd(gpg, "--armor", "--export",
                           "-o", fpath, gpg_user)

        cmd.execute()
        print(cmd.result)

    def import_public(self, fpath, sign=False):
        """
        import a key, can locally sign it too
        """
        if not (fpath and fpath.exists()):
            return False

        cmd = self.cmd(gpg, "--batch", "--import", fpath)
        cmd.execute()
        print(cmd.result)

        if sign:
            name = input("Public Key: ")
            cmd = self.cmd(gpg, "--lsign-key", name)
            cmd.execute()
            print(cmd.result)

    def delete_key(self, user=None, secret=False):
        """
        delete a key from the keychain
        """
        user = user or gpg_user
        if secret:
            sec_cmd = self.cmd(gpg, "--delete-secret-keys", user)
            sec_cmd.execute()
            print(sec_cmd.result)

        cmd = self.cmd(gpg, "--delete-keys", user)
        cmd.execute()
        print(cmd.result)

    def new_key(self):
        """
        add a new key to the keychain
        plus add a recoke certificate
        """
        cmd = self.interact(gpg, "--gen-key")
        cmd.execute()
        print(cmd.result)

        rev_cmd = self.cmd(gpg, "--gen-revoke", "--armor",
                           "-o", self.locs.secrets / "revoke_cert.asc",
                           gpg_user)

        rev_cmd.execute()
        print(rev_cmd.result)

    def encrypt(self, fpath, *others, safe=True, self_decrypt=True):
        """
        encrypt a file, if not safe, delete the original, if not self_decrypt don't add self as a recipient
        """
        if not self_decrypt:
            logging.warning("Not Including Self as Recipient")
            users = list(others)
        else:
            users = [gpg_user, *others]

        recipients = [x for pair in zip(["-r"] * len(users), users) for x in pair]

        cmd = self.interact(gpg, "--sign", "--armor", "--batch",
                       "-u", gpg_user,
                       *recipients,
                       "-o", fpath.with_suffix(fpath.suffix + ".gpg"),
                       "-e", fpath)
        cmd.execute()
        print(cmd.result)

        if not safe and fpath.with_suffix(fpath.suffix + ".gpg").exists():
            fpath.unlink()

    def decrypt(self, fpath, output=None):
        """
        decrypt a file, outputing to fpath without the suffix by default
        """
        output = output or fpath.with_suffix("")
        cmd = self.cmd(gpg, "--batch",
                       "-o", output,
                       "-d", fpath)

        cmd.execute()
        print(cmd.result)

    def sign(self, fpath, detached=False):
        """
        ClearSign a file, optionally detached
        """
        if detached:
            cmd = self.cmd(gpg, "--detach-sign", "--clearsign", fpath)
        else:
            cmd = self.cmd(gpg, "--clearsign", fpath)
        cmd.execute()
        print(cmd.result)

    def verify(self, fpath):
        """
        Verify a signature
        """
        cmd = self.cmd(gpg, "--verify", fpath)
        cmd.execute()
        print(cmd.result)
