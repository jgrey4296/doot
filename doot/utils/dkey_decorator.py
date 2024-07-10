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
import keyword
import inspect
import more_itertools as mitz
from pydantic import BaseModel, Field, field_validator, model_validator
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import Key_p, SpecStruct_p, Decorator_p
from doot._structs.code_ref import CodeReference
from doot.utils.decorators import DecorationUtils, DootDecorator
from doot._structs.dkey import DKey

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

KEY_PATTERN                                = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                         = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                          = doot.constants.patterns.STATE_TASK_NAME_K
ARGS_K         : Final[str]                = "args"
KWARGS_K       : Final[str]                = "kwargs"

PATTERN        : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN   : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"

class DKeyed:
    """ Decorators for actions

    It registers arguments on an action and extracts them from the spec and state automatically.

    provides: expands/paths/types/requires/returns/args/kwargs/redirects
    The kwarg 'hint' takes a dict and passes the contents to the relevant expansion method as kwargs

    arguments are added to the tail of the action args, in order of the decorators.
    the name of the expansion is expected to be the name of the action parameter,
    with a "_" prepended if the name would conflict with a keyword., or with "_ex" as a suffix
    eg: @DKeyed.paths("from") -> def __call__(self, spec, state, _from):...
    or: @DKeyed.paths("from") -> def __call__(self, spec, state, from_ex):...
    """

    @staticmethod
    def get_keys(fn) -> list[DKey]:
        """ Retrieve key annotations from a decorated function """
        dec = DKeyExpansionDecorator([])
        return dec.get_annotations(fn)

    @staticmethod
    def taskname(fn):
        keys = [DKey(STATE_TASK_NAME_K, mark=DKey.mark.TASK)]
        return DKeyExpansionDecorator(keys)(fn)

    @staticmethod
    def formats(*args, **kwargs):
        keys     = [DKey(x, mark=DKey.mark.STR, **kwargs) for x in args]
        return DKeyExpansionDecorator(keys)

    @staticmethod
    def expands(*args, **kwargs):
        """ mark an action as using expanded string keys """
        return DKeyed.formats(*args, **kwargs)

    @staticmethod
    def paths(*args, **kwargs):
        """ mark an action as using expanded path keys """
        keys = [DKey(x, mark=DKey.mark.PATH, **kwargs) for x in args]
        return DKeyExpansionDecorator(keys)

    @staticmethod
    def types(*args, **kwargs):
        """ mark an action as using raw type keys """
        keys = [DKey(x, mark=DKey.mark.FREE, **kwargs) for x in args]
        return DKeyExpansionDecorator(keys)

    @staticmethod
    def args(fn):
        """ mark an action as using spec.args """
        keys = [DKey(ARGS_K, mark=DKey.mark.ARGS)]
        return DKeyExpansionDecorator(keys)(fn)

    @staticmethod
    def kwargs(fn):
        """ mark an action as using all kwargs"""
        keys = [DKey(KWARGS_K, mark=DKey.mark.KWARGS)]
        return DKeyExpansionDecorator(keys)(fn)

    @staticmethod
    def redirects(*args, **kwargs):
        """ mark an action as using redirection keys """
        keys = [DKey(x, mark=DKey.mark.REDIRECT, ctor=DKey, **kwargs) for x in args]
        return DKeyExpansionDecorator(keys)

    @staticmethod
    def references(*args, **kwargs):
        """ mark keys to use as to_coderef imports """
        keys = [DKey(x, mark=DKey.mark.CODE, **kwargs) for x in args]
        return DKeyExpansionDecorator(keys)

    @staticmethod
    def postbox(*args, **kwargs):
        keys = [DKey(x, mark=DKey.mark.POSTBOX, **kwargs) for x in args]
        return DKeyExpansionDecorator(keys)

    @staticmethod
    def requires(*args, **kwargs):
        """ mark an action as requiring certain keys to be passed in """
        keys = [DKey(x, mark=DKey.mark.NULL, **kwargs) for x in args]
        return DKeyMetaDecorator(keys)

    @staticmethod
    def returns(*args, **kwargs):
        """ mark an action as needing to return certain keys """
        keys = [DKey(x, mark=DKey.mark.NULL, **kwargs) for x in args]
        return DKeyMetaDecorator(keys)

class DKeyExpansionDecorator(Decorator_p):
    """
    Utility class for idempotently decorating actions with auto-expanded keys
    """

    def __init__(self, keys, *, prefix=None, mark=None, data=None, ignores=None):
        self._data              = keys
        self._annotation_prefix = prefix  or "__DOOT_ANNOTATIONS__"
        self._mark_suffix       = mark    or "_keys_expansion_handled_"
        self._data_suffix       = data    or "_expansion_keys"
        self._param_ignores     = ignores or ["_", "_ex"]
        self._mark_key          = f"{self._annotation_prefix}:{self._mark_suffix}"
        self._data_key          = f"{self._annotation_prefix}:{self._data_suffix}"

    def __call__(self, fn):
        if not bool(self._data):
            return fn

        orig = fn
        fn   = self._unwrap(fn)
        # update annotations
        total_annotations = self._update_annotations(fn)

        if not self._verify_action(fn, total_annotations):
            raise doot.errors.DootKeyError("Annotations do not match signature", orig, fn, total_annotations)

        if self._is_marked(fn):
            self._update_annotations(orig)
            return orig

        # add wrapper
        is_func = inspect.signature(fn).parameters.get("self", None) is None

        match is_func:
            case False:
                wrapper = self._target_method(fn)
            case True:
                wrapper = self._target_fn(fn)

        return self._apply_mark(wrapper)

    def get_annotations(self, fn):
        fn = self._unwrap(fn)
        return getattr(fn, self._data_key, [])

    def _unwrap(self, fn) -> Callable:
        return inspect.unwrap(fn)

    def _target_method(self, fn) -> Callable:
        data_key = self._data_key

        @ftz.wraps(fn)
        def method_action_expansions(self, spec, state, *call_args, **kwargs):
            try:
                expansions = [x(spec, state) for x in getattr(fn, data_key)]
            except KeyError as err:
                printer.warning("Action State method Expansion Failure: %s", err)
                return False
            else:
                all_args = (*call_args, *expansions)
                return fn(self, spec, state, *all_args, **kwargs)

        # -
        return method_action_expansions

    def _target_fn(self, fn) -> Callable:
        data_key = self._data_key

        @ftz.wraps(fn)
        def fn_action_expansions(spec, state, *call_args, **kwargs):
            try:
                expansions = [x(spec, state) for x in getattr(fn, data_key)]
            except KeyError as err:
                printer.warning("Action State fn Expansion Failure: %s", err)
                return False
            else:
                all_args = (*call_args, *expansions)
                return fn(spec, state, *all_args, **kwargs)

        # -
        return fn_action_expansions

    def _target_class(self, cls) -> type:
        original = cls.__call__
        cls.__call__ = self._target_method(cls.__call__)
        return cls

    def _update_annotations(self, fn) -> list:
        # prepend annotations, so written decorator order is the same as written arg order:
        # (ie: @wrap(x) @wrap(y) @wrap(z) def fn (x, y, z), even though z's decorator is applied first
        new_annotations = self._data + getattr(fn, self._data_key, [])
        setattr(fn, self._data_key, new_annotations)
        return new_annotations

    def _is_marked(self, fn) -> bool:
        match fn:
            case type():
                return hasattr(fn, self._mark_key) or (fn.__call__, self._mark_key)
            case _:
                return hasattr(fn, self._mark_key)

    def _apply_mark(self, fn:Callable) -> Callable:
        unwrapped = self._unwrap(fn)
        setattr(unwrapped, self._mark_key, True)
        if unwrapped is not fn:
            setattr(fn, self._mark_key, True)

        return fn

    def _verify_action(self, fn, args) -> bool:
        match fn:
            case inspect.Signature():
                sig = fn
            case _:
                sig = inspect.signature(fn, follow_wrapped=False)

        match sig.parameters.get("self", None):
            case None:
                head_sig = ["spec", "state"]
            case _:
                head_sig = ["self", "spec", "state"]

        return self._verify_signature(sig, head_sig, args)

    def _verify_signature(self, sig:Callable|inspect.Signature, head:list, tail=None) -> bool:
        match sig:
            case inspect.Signature():
                pass
            case _:
                sig = inspect.signature(sig)

        params      = list(sig.parameters)
        tail        = tail or []

        for x,y in zip(params, head):
            if x != y:
                logging.debug("Mismatch in signature head: %s != %s", x, y)
                return False

        prefix_ig, suffix_ig = self._param_ignores
        for x,y in zip(params[::-1], tail[::-1]):
            key_str = str(y)
            if x.startswith(prefix_ig) or x.endswith(suffix_ig):
                logging.debug("Skipping: %s", x)
                continue

            if keyword.iskeyword(key_str):
                logging.debug("Key is a keyword, the function sig needs to use _{} or {}_ex: %s : %s", x, y)
                return False

            if not key_str.isidentifier():
                logging.debug("Key is not an identifier, the function sig needs to use _{} or {}_ex: %s : %s", x,y)
                return False

            if x != y:
                logging.debug("Mismatch in signature tail: %s != %s", x, y)
                return False

        return True

class DKeyMetaDecorator(DKeyExpansionDecorator):

    def __init__(self, keys):
        super().__init__(keys, mark="meta_key_mark", data="meta_keys")

    def __call__(self, fn):
        if not bool(self._data):
            return fn

        orig = fn
        fn   = self._unwrap(fn)
        total_annotations = self._update_annotations(fn)

        if self._is_marked(fn):
            self._update_annotations(orig)

        return orig
