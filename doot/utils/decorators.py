#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
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
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import keyword
import inspect
import abc
import builtins
from typing import Type
import decorator
import doot
import doot.errors
from doot.enums import LocationMeta
from doot._abstract.protocols import SpecStruct_p

DOOT_ANNOTATIONS : Final[str]                = "__DOOT_ANNOTATIONS__"
KEYS_HANDLED     : Final[str]                = "_doot_keys_handler"
ORIG_ARGS        : Final[str]                = "_doot_orig_args"
KEY_ANNOTATIONS  : Final[str]                = "_doot_keys"
FUNC_WRAPPED     : Final[str]                = "__wrapped__"
PARAM_PREFIX     : Final[str]                = "_"
PARAM_SUFFIX     : Final[str]                = "_ex"

class DecorationUtils:
    """
      utilities for decorators
    """

    _annot        = DOOT_ANNOTATIONS
    _keys         = KEY_ANNOTATIONS
    _wrapped_flag = KEYS_HANDLED

    @staticmethod
    def unwrap(fn:callable) -> callable:
        # if not hasattr(fn, FUNC_WRAPPED):
        #     return fn

        # return getattr(fn, FUNC_WRAPPED)
        return inspect.unwrap(fn)

    @staticmethod
    def verify_signature(fn, head:list, tail:list=None) -> bool:
        """
          Inspect the signature of a function, an check the parameter names are correct
        """
        match fn:
            case inspect.Signature():
                sig = fn
            case _:
                sig = inspect.signature(fn, follow_wrapped=False)

        params      = list(sig.parameters)
        tail        = tail or []

        for x,y in zip(params, head):
            if x != y:
                logging.debug("Mismatch in signature head: %s != %s", x, y)
                return False

        for x,y in zip(params[::-1], tail[::-1]):
            key_str = str(y)
            if x.startswith(PARAM_PREFIX) or x.endswith(PARAM_SUFFIX):
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

    @staticmethod
    def verify_action_signature(fn:Signature|callable, args:list) -> bool:
        """
          verify that a callable signature is [self?, spec, state, *keys]
        """
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

        return DecorationUtils.verify_signature(sig, head_sig, args)

    @staticmethod
    def manipulate_signature(fn, args) -> callable:
        raise NotImplementedError()

    @staticmethod
    def truncate_signature(fn):
        """
           actions are (self?, spec, state)
          with and extracted keys from the spec and state.
          This truncates the signature of the action to what is *called*, not what is *used*.

          TODO: could take a callable as the prototype to build the signature from
        """
        sig              = inspect.signature(fn)
        min_index        = len(sig.parameters) - len(getattr(fn, DecorationUtils._keys))
        newsig           = sig.replace(parameters=list(sig.parameters.values())[:min_index])
        fn.__signature__ = newsig
        return fn

    @staticmethod
    def has_annotations(fn, *keys) -> bool:
        """
          test a function for doot annotations
          unwraps a function if necessary
        """
        unwrapped = DecorationUtils.unwrap(fn)
        if not hasattr(unwrapped, DecorationUtils._annot):
            return False

        annots = getattr(unwrapped, DecorationUtils._annot)
        return all(key in annots for key in keys)

    @staticmethod
    def annotate(fn:callable, annots:dict|set) -> callable:
        """
          Annotate a function with additional information
          applies update to the wrapper and wrapped

          a dict updates the function dict directory,
          a set gets added to DecorationUtils._annot
        """
        unwrapped = DecorationUtils.unwrap(fn)
        match annots:
            case dict():
                unwrapped.__dict__.update(annots)
                if fn is not unwrapped:
                    fn.__dict__.update(annots)
                return fn
            case set() if not hasattr(unwrapped, DecorationUtils._annot):
                new_set = set()
                setattr(unwrapped, DecorationUtils._annot, new_set)
                if fn is not unwrapped:
                    setattr(fn, DecorationUtils._annot, new_set)
            case set():
                pass
            case _:
                raise TypeError("Tried to annotate a function with an unknown type", annots)

        annotations = getattr(unwrapped, DecorationUtils._annot)
        annotations.update(annots)

        return fn

    @staticmethod
    def _update_key_annotations(fn, keys:list[DootKey]) -> True:
        """ update the declared expansion keys on an action
          If the action has been wrapped already, annotations will be applied to both the wrapper and wrapped.
        """
        unwrapped = DecorationUtils.unwrap(fn)
        sig = inspect.signature(unwrapped)

        # prepend annotations, so written decorator order is the same as written arg order:
        # (ie: @wrap(x) @wrap(y) @wrap(z) def fn (x, y, z), even though z's decorator is applied first
        new_annotations = keys + getattr(unwrapped, DecorationUtils._keys, [])
        setattr(unwrapped, DecorationUtils._keys, new_annotations)
        if unwrapped is not fn:
            setattr(fn, DecorationUtils._keys, new_annotations)

        if not DecorationUtils.verify_action_signature(sig, new_annotations):
            raise doot.errors.DootKeyError("Annotations do not match signature", sig)

        return True

    @staticmethod
    def prepare_expansion(keys:list[DootKey], fn):
        """ used as a partial fn. adds declared keys to a function,
          and idempotently adds the expansion decorator
        """
        is_func = True
        DecorationUtils._update_key_annotations(fn, keys)

        if DecorationUtils.has_annotations(fn, DecorationUtils._wrapped_flag):
            # keys are handled, so the fn already has an expander, no need to add one
            return fn

        is_func = inspect.signature(fn).parameters.get("self", None) is None
        match is_func:
            case False:
                wrapper = DecorationUtils.add_method_expander(fn)
            case True:
                wrapper = DecorationUtils.add_fn_expander(fn)

        # mark the function as having a wrapper installed
        DecorationUtils.annotate(fn, {DecorationUtils._wrapped_flag})
        return wrapper

    @staticmethod
    def add_method_expander(fn):

        @ftz.wraps(fn)
        def method_action_expansions(self, spec, state, *call_args, **kwargs):
            try:
                expansions = [x(spec, state) for x in getattr(fn, DecorationUtils._keys)]
            except KeyError as err:
                printer.warning("Action State Expansion Failure: %s", err)
                return False
            all_args = (*call_args, *expansions)
            return fn(self, spec, state, *all_args, **kwargs)

        # -
        return method_action_expansions

    @staticmethod
    def add_fn_expander(fn):

        @ftz.wraps(fn)
        def fn_action_expansions(spec, state, *call_args, **kwargs):
            try:
                expansions = [x(spec, state) for x in getattr(fn, DecorationUtils._keys)]
            except KeyError as err:
                printer.warning("Action State Expansion Failure: %s", err)
                return False
            all_args = (*call_args, *expansions)
            return fn(spec, state, *all_args, **kwargs)

        # -
        return fn_action_expansions

class DootDecorator(abc.ABC):
    """ Base Class for decorators that annotate action callables
      set self._annotations:dict to add annotations to fn.__DOOT_ANNOTATIONS (:set)
      implement self._wrapper to add a wrapper around the fn.
      TODO: set self._idempotent=True to only add a wrapper once
      """

    def __init__(self):
        self._idempotent  = False
        self._annotations =  set()

    def __call__(self, fn):
        if bool(self._annotations):
            DecorationUtils.annotate(fn, self._annotations)

        if not hasattr(self, "_wrapper"):
            return fn

        if isinstance(fn, Type):
            return self._decorate_class(fn)

        match DecorationUtils.verify_signature(fn, ["self"]):
            case True:

                @ftz.wraps(fn)
                def decorated(obj, *args, **kwargs):
                    return self._wrapper(self._prep_method(fn, obj), *args, **kwargs, _obj=obj)

            case False:

                @ftz.wraps(fn)
                def decorated(*args, **kwargs):
                    return self._wrapper(fn, *args ,**kwargs)

        return decorated

    def _decorate_class(self, cls):
        original = cls.__call__

        @ftz.wraps(cls.__call__)
        def decorated(obj, *args, **kwargs):
            return self._wrapper(self._prep_method(original, obj), *args, **kwargs, _obj=original)

        cls.__call__ = decorated
        return cls

    def _prep_method(self, fn, obj):
        return ftz.partial(fn, obj)
