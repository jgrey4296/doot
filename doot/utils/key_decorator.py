#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import decorator
import more_itertools as mitz
from pydantic import BaseModel, Field, field_validator, model_validator
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._structs.key import DootKey, DootArgsKey, DootKwargsKey
from doot._abstract.protocols import Key_p, SpecStruct_p
from doot._structs.code_ref import CodeReference
from doot.utils.chain_get import DootKeyGetter
from doot.utils.decorators import DecorationUtils, DootDecorator

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

KEY_PATTERN                                = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                         = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                          = doot.constants.patterns.STATE_TASK_NAME_K

PATTERN        : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN   : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"



class Keyed:
    """ Decorators for actions
    KeyDecorator is accessible as DootKey.dec

    It registers arguments on an action and extracts them from the spec and state automatically.

    provides: expands/paths/types/requires/returns/args/kwargs/redirects/redirects_many

    The kwarg 'hint' takes a dict and passes the contents to the relevant expansion method as kwargs

    arguments are added to the tail of the action args, in order of the decorators.
    the name of the expansion is expected to be the name of the action parameter,
    with a "_" prepended if the name would conflict with a keyword., or with "_ex" as a suffix
    eg: @DootKey.kwrap.paths("from") -> def __call__(self, spec, state, _from):...
    or: @DootKey.kwrap.paths("from") -> def __call__(self, spec, state, from_ex):...
    """

    @staticmethod
    def get_keys(fn) -> list[DootKey]:
        fn = DecorationUtils.unwrap(fn)
        return getattr(fn, DecorationUtils._keys, [])

    @staticmethod
    def taskname(fn):
        keys = [DootKey.build(STATE_TASK_NAME_K, exp_hint="type")]
        return DecorationUtils.prepare_expansion(keys, fn)

    @staticmethod
    def expands(*args, hint:dict|None=None, **kwargs):
        """ mark an action as using expanded string keys """
        exp_hint = {"expansion": "str", "kwargs" : hint or {} }
        keys     = [DootKey.build(x, exp_hint=exp_hint, **kwargs) for x in args]
        return ftz.partial(DecorationUtils.prepare_expansion, keys)

    @staticmethod
    def paths(*args, hint:dict|None=None, **kwargs):
        """ mark an action as using expanded path keys """
        exp_hint = {"expansion": "path", "kwargs" : hint or {} }
        keys = [DootKey.build(x, exp_hint=exp_hint, **kwargs) for x in args]
        return ftz.partial(DecorationUtils.prepare_expansion, keys)

    @staticmethod
    def types(*args, hint:dict|None=None, **kwargs):
        """ mark an action as using raw type keys """
        exp_hint = {"expansion": "type", "kwargs" : hint or {} }
        keys = [DootKey.build(x, exp_hint=exp_hint, **kwargs) for x in args]
        return ftz.partial(DecorationUtils.prepare_expansion, keys)

    @staticmethod
    def args(fn):
        """ mark an action as using spec.args """
        # TODO handle expansion hint for the args
        keys = [DootArgsKey("args")]
        return DecorationUtils.prepare_expansion(keys, fn)

    @staticmethod
    def kwargs(fn):
        """ mark an action as using all kwargs"""
        keys = [DootKwargsKey("kwargs")]
        return DecorationUtils.prepare_expansion(keys, fn)

    @staticmethod
    def redirects(*args):
        """ mark an action as using redirection keys """
        keys = [DootKey.build(x, exp_hint="redirect") for x in args]
        return ftz.partial(DecorationUtils.prepare_expansion, keys)

    @staticmethod
    def redirects_many(*args, **kwargs):
        """ mark an action as using redirection key lists """
        keys = [DootKey.build(x, exp_hint="redirect_multi") for x in args]
        return ftz.partial(DecorationUtils.prepare_expansion, keys)

    @staticmethod
    def requires(*args, **kwargs):
        """ TODO mark an action as requiring certain keys to be passed in """
        keys = [DootKey.build(x, **kwargs) for x in args]
        # return ftz.partial(DecorationUtils.prepare_expansion, keys)
        return lambda x: x

    @staticmethod
    def returns(*args, **kwargs):
        """ mark an action as needing to return certain keys """
        keys = [DootKey.build(x, **kwargs) for x in args]
        # return ftz.partial(DecorationUtils.prepare_expansion, keys)
        return lambda x: x

    @staticmethod
    def references(*args, **kwargs):
        """ mark keys to use as to_coderef imports """
        exp_hint = {"expansion": "coderef", "kwargs" : {} }
        keys = [DootKey.build(x, exp_hint=exp_hint, **kwargs) for x in args]
        return ftz.partial(DecorationUtils.prepare_expansion, keys)
