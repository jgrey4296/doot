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

import abc
from collections import UserString
import string
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.constants import KEY_PATTERN, MAX_KEY_EXPANSIONS
from doot._structs.action_spec import DootActionSpec
from doot._structs.artifact import DootTaskArtifact

PATTERN        : Final[re.Pattern]         = re.compile("{(.+?)}")
FAIL_PATTERN   : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
KEYS_HANDLED   : Final[str]                = "_doot_keys_handler"
ORIG_ARGS      : Final[str]                = "_doot_orig_args"
KEY_ANNOTS     : Final[str]                = "_doot_keys"
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"
FUNC_WRAPPED   : Final[str]                = "__wrapped__"

class KWrapper:
    """ Decorators for actions """

    @staticmethod
    def _annotate_keys(f, keys:list) -> bool:
        """ cache original args, and cache declared keys """
        if hasattr(f, FUNC_WRAPPED):
            # Deal with the actual function, not any decorators
            return KWrapper._annotate_keys(f.__wrapped__, keys)

        if not hasattr(f, ORIG_ARGS):
            # store the original arguments for easy access
            setattr(f, ORIG_ARGS, f.__code__.co_varnames[:f.__code__.co_argcount])
        if not hasattr(f, KEY_ANNOTS):
            # ensure theres a place for annotations
            setattr(f, KEY_ANNOTS, [])
        # prepend annotations, so written decorator order is the same as written arg order:
        # (ie: @wrap(x) @wrap(y) @wrap(z) def f (x, y, z), even though z's decorator is applied first
        new_annotations = keys + getattr(f, KEY_ANNOTS)
        setattr(f, KEY_ANNOTS, new_annotations)

        # run the key check
        if not KWrapper._check_keys(f, getattr(f, KEY_ANNOTS)):
            raise doot.errors.DootKeyError("Annotations do not match signature", getattr(f, ORIG_ARGS, []), getattr(f, KEY_ANNOTS), f.__qualname__)

        return True

    @staticmethod
    def _annotate_non_expansions(f, keys:list, type_="in") -> bool:
        """
        Annotate required inputs and output
        """
        if hasattr(f, FUNC_WRAPPED):
            return KWrapper._annotate_non_expansions(f.__wrapped__, keys)

    @staticmethod
    def _check_keys(f, keys, offset=0) -> bool:
        """ test declared args to a list of keys """
        if hasattr(f, ORIG_ARGS):
            code_args           = getattr(f, ORIG_ARGS)
            code_argcount       = len(code_args)
        else:
            code_argcount           = f.__code__.co_argcount
            code_args               = f.__code__.co_varnames[:code_argcount]

        result                  = True
        if code_args[0]         == "self":
            code_args           = code_args[1:]

        # First two params should always be spec and state
        result &= code_args[:2] == ("spec", "state")

        # The rest should match keys
        for actual, expected in zip(code_args[:1+offset:-1], keys[::-1]):
            match expected:
                case DootMultiKey() | DootPathKey():
                    pass
                case DootSimpleKey() | str() if actual.startswith("_"):
                    pass
                case DootSimpleKey() | str():
                    result &= ((actual == expected) or (actual == f"{expected}_ex"))

        return result

    @staticmethod
    def _add_key_handler(f):
        """ a general flat key handler so decorated functions dont need multiples """
        if getattr(f, KEYS_HANDLED, False):
            return f

        match getattr(f, ORIG_ARGS)[0]:
            case "self":
                @ftz.wraps(f)
                def action_expands(self, spec, state, *call_args, **kwargs):
                    expansions = [x(spec, state) for x in getattr(f, KEY_ANNOTS)]
                    all_args = (*call_args, *expansions)
                    return f(self, spec, state, *all_args, **kwargs)
            case _:
                @ftz.wraps(f)
                def action_expands(spec, state, *call_args, **kwargs):
                    expansions = [x(spec, state) for x in getattr(f, KEY_ANNOTS)]
                    all_args = (*call_args, *expansions)
                    return f(spec, state, *all_args, **kwargs)

        setattr(action_expands, KEYS_HANDLED, True)
        return action_expands

    @staticmethod
    def expands(*args, hint:dict|None=None, **kwargs):
        """ mark an action as using expanded string keys """
        exp_hint = {"expansion": "str", "kwargs" : hint or {} }
        keys = [DootKey.make(x, exp_hint=exp_hint, **kwargs) for x in args]

        def expand_wrapper(f):
            KWrapper._annotate_keys(f, keys)
            return KWrapper._add_key_handler(f)

        return expand_wrapper

    @staticmethod
    def paths(*args, hint:dict|None=None, **kwargs):
        """ mark an action as using expanded path keys """
        exp_hint = {"expansion": "path", "kwargs" : hint or {} }
        keys = [DootKey.make(x, exp_hint=exp_hint, **kwargs) for x in args]

        def expand_wrapper(f):
            KWrapper._annotate_keys(f, keys)
            return KWrapper._add_key_handler(f)

        return expand_wrapper

    @staticmethod
    def types(*args, hint:dict|None=None, **kwargs):
        """ mark an action as using raw type keys """
        exp_hint = {"expansion": "type", "kwargs" : hint or {} }
        keys = [DootKey.make(x, exp_hint=exp_hint, **kwargs) for x in args]

        def expand_wrapper(f):
            KWrapper._annotate_keys(f, keys)
            return KWrapper._add_key_handler(f)

        return expand_wrapper

    @staticmethod
    def args(f):
        """ mark an action as using spec.args """
        # TODO handle expansion hint for the args
        KWrapper._annotate_keys(f, [DootArgsKey("args")])
        return KWrapper._add_key_handler(f)

    @staticmethod
    def kwargs(f):
        """ mark an action as using spec.args """
        KWrapper._annotate_keys(f, [DootKwargsKey("kwargs")])
        return KWrapper._add_key_handler(f)

    @staticmethod
    def redirects(*args):
        """ mark an action as using redirection keys """
        keys = [DootKey.make(x, exp_hint="redirect") for x in args]

        def expand_wrapper(f):
            KWrapper._annotate_keys(f, keys)
            return KWrapper._add_key_handler(f)

        return expand_wrapper

    @staticmethod
    def redirects_many(*args, **kwargs):
        """ mark an action as using redirection key lists """
        keys = [DootKey.make(x, exp_hint="redirect_multi") for x in args]

        def expand_wrapper(f):
            KWrapper._annotate_keys(f, keys)
            return KWrapper._add_key_handler(f)

        return expand_wrapper

    @staticmethod
    def requires(*args, **kwargs):
        """ mark an action as requiring certain keys to be passed in """
        keys = [DootKey.make(x, **kwargs) for x in args]
        def expand_wrapper(f):
            KWrapper._annotate_non_expansions(f, keys)
            return f

        return expand_wrapper

    @staticmethod
    def returns(*args, **kwargs):
        """ mark an action as needing to return certain keys """
        keys = [DootKey.make(x, **kwargs) for x in args]
        def expand_wrapper(f):
            KWrapper._annotate_non_expansions(f, keys)
            return f

        return expand_wrapper

class DootFormatter(string.Formatter):
    """
      A Formatter for expanding arguments based on action spec kwargs, and task state, and cli args
    """
    _fmt = None

    @staticmethod
    def fmt(fmt:str|DootKey|pl.Path, /, *args, **kwargs) -> str:
        if not DootFormatter._fmt:
            DootFormatter._fmt = DootFormatter()

        return DootFormatter._fmt.format(fmt, *args, **kwargs)

    def format(self, fmt:str|DootKey|pl.Path, /, *args, **kwargs) -> str:
        self._depth = 0
        match kwargs.get("_spec", None):
            case None:
                kwargs['_spec'] = {}
            case DootActionSpec():
                kwargs['_spec'] = kwargs['_spec'].kwargs
            case x:
                raise TypeError("Bad Spec Type in Format Call", x)

        match fmt:
            case DootKey():
                fmt = fmt.form
                result = self.vformat(fmt, args, kwargs)
            case str():
                result = self.vformat(fmt, args, kwargs)
            # case pl.Path():
            #     result = str(ftz.reduce(pl.Path.joinpath, [self.vformat(x, args, kwargs) for x in fmt.parts], pl.Path()))
            case _:
                raise TypeError("Unrecognized expansion type", fmt)

        return result

    def get_value(self, key, args, kwargs):
        logging.debug("Expanding: %s", key)
        if isinstance(key, int):
            return args[key]

        insist            = kwargs.get("_insist", False)
        state             = kwargs.get('_state', None) or {}
        locs              = kwargs.get("_locs", None)
        cli               = doot.args.on_fail({}).tasks[str(state.get('_task_name', None))]()
        replacement       = cli.get(key, None)
        if replacement is None:
            spec        = kwargs.get('_spec')
            replacement = spec.get(key, None)
        if replacement is None:
            replacement = state.get(key, None)
        if replacement is None and locs is not None:
            match locs.get(key, None):
                case None:
                    pass
                case pl.Path() as x:
                    replacement = locs.normalize(x)

        match replacement:
            case None if insist:
                raise KeyError("Key Expansion Not Found")
            case None:
                return DootKey.make(key).form
            case DootKey() if self._depth < MAX_KEY_EXPANSIONS:
                self._depth += 1
                return self.vformat(replacement.form, args, kwargs)
            case str() if kwargs.get("_rec", False) and self._depth < MAX_KEY_EXPANSIONS:
                self._depth += 1
                return self.vformat(str(replacement), args, kwargs)
            case str():
                return replacement
            case pl.Path() if self._depth < MAX_KEY_EXPANSIONS:
                self._depth += 1
                return ftz.reduce(pl.Path.joinpath, map(lambda x: self.vformat(x, args, kwargs), replacement.parts), pl.Path())
            case _:
                return str(replacement)
                # raise TypeError("Replacement Value isn't a string", args, kwargs)

class DootKey(abc.ABC):
    """ A shared, non-functional base class for DootKeys and variants like DootMultiKey.
      Use DootKey.make for constructing keys

      DootSimpleKeys are strings, wrapped in {} when used in toml.
      so DootKey.make("blah") -> DootSimpleKey("blah") -> DootSimpleKey('blah').form =="{blah}" -> [toml] aValue = "{blah}"

      DootMultiKeys are containers of a string `value`, and a list of SimpleKeys the value contains.
      So DootKey.make("{blah}/{bloo}") -> DootMultiKey("{blah}/{bloo}", [DootSimpleKey("blah", DootSimpleKey("bloo")]) -> .form == "{blah}/{bloo}"
    """
    kwrap = KWrapper

    @staticmethod
    def make(s:str|DootKEy|DootTaskArtifact|pl.Path|dict, *, strict=False, explicit=False, exp_hint:str|dict=None, help=None) -> DootKey:
        """ Make an appropriate DootKey based on input value
          Can only create MultiKeys if strict = False,
          if explicit, only keys wrapped in {} are made, everything else is returned untouched
          if strict, then only simple keys can be returned
        """
        # TODO annotate with 'help'
        # TODO store expansion args on make
        result = s
        match s:
            case { "path": x }:
                result = DootPathKey(x)
                exp_hint = "path"
            case DootSimpleKey() if strict:
                result = s
            case DootKey():
                result = s
            case str() if not (s_keys := PATTERN.findall(s)) and not explicit:
                result = DootSimpleKey(s)
            case str() if not s_keys and explicit:
                result = DootNonKey(s)
            case str() if len(s_keys) == 1 and s_keys[0] == s[1:-1]:
                result = DootSimpleKey(s[1:-1])
            case str() if not strict:
                result = DootMultiKey(s)
            case DootTaskArtifact(path=path) | (pl.Path() as path) if not strict:
                result = DootMultiKey(path)
            case _:
                raise TypeError("Bad Type to build a Doot Key Out of", s)

        if exp_hint is not None:
            result.set_expansion_hint(exp_hint)

        return result

    def set_help(self, help:str):
        setattr(self, HELP_HINT, help)

    def set_expansion_hint(self, etype:str|dict):
        match etype:
            case "str" | "path" | "type" | "redirect" | "redirect_multi":
                setattr(self, EXPANSION_HINT, {"expansion": etype, "kwargs": {}})
            case {"expansion": str(), "kwargs": dict()}:
                setattr(self, EXPANSION_HINT, etype)
            case _:
                raise doot.errors.DootKeyError("Bad Key Expansion Type Declared", self, etype)

    def __call__(self, spec, state):
        """ Expand the key using the registered expansion hint """
        match getattr(self, EXPANSION_HINT, False):
            case False:
                raise doot.errors.DootKeyError("No Default Key Expansion Type Declared", self)
            case {"expansion": "str", "kwargs": kwargs}:
                return self.expand(spec, state, **kwargs)
            case {"expansion": "path", "kwargs": kwargs}:
                return self.to_path(spec, state, **kwargs)
            case {"expansion" : "type", "kwargs" : kwargs}:
                return self.to_type(spec, state, **kwargs)
            case {"expansion": "redirect"}:
                return self.redirect(spec)
            case {"expansion": "redirect_multi"}:
                return self.redirect_multi(spec)
            case x:
                raise doot.errors.DootKeyError("Key Called with Bad Key Expansion Type", self, x)

    @property
    def form(self) -> str:
        return str(self)

    @property
    def is_indirect(self) -> bool:
        return False

    def redirect(self, spec=None) -> DootKey:
        return self

    def to_path(self, spec=None, state=None, chain:list[DootKey]=None, locs:DootLocations=None, on_fail:None|str|pl.Path|DootKey=Any, symlinks=False) -> pl.Path:
        """
          Convert a key to an absolute path
        """
        locs                 = locs or doot.locs
        key : pl.Path        = pl.Path(self.redirect(spec).form)

        try:
            expanded         : list       = [DootFormatter.fmt(x, _spec=spec, _state=state, _rec=True) for x in key.parts]
            expanded_as_path : pl.Path    = pl.Path().joinpath(*expanded)
            depth                         = 0
            while PATTERN.search(str(expanded_as_path)) and depth < MAX_KEY_EXPANSIONS:
                to_keys          : list       = [DootKey.make(x, explicit=True) or x for x in expanded_as_path.parts]
                loc_expansions   : list       = [locs.get(x) for x in to_keys]
                expanded_as_path : pl.Path    = pl.Path().joinpath(*loc_expansions)
                depth += 1

            if any(bool(matches) for x in expanded_as_path.parts if (matches:=PATTERN.findall(x))):
                raise doot.errors.DootLocationExpansionError("Missing keys on path expansion", matches, self)

            return locs.normalize(expanded_as_path, symlinks=symlinks)

        except doot.errors.DootLocationExpansionError as err:
            if bool(chain):
                return chain[0].to_path(spec, state, chain=chain[1:], on_fail=on_fail, symlinks=symlinks)
            match on_fail:
                case None:
                    return None
                case DootKey():
                    return on_fail.to_path(spec, state, symlinks=symlinks)
                case pl.Path() | str():
                    return locs.normalize(pl.Path(on_fail),  symlinks=symlinks)
                case _:
                    raise err

    def within(self, other:str|dict|TomlGuard) -> bool:
        return False

    @abc.abstractmethod
    def to_type(self, spec, state, type_=Any, chain:list[DootKey]=None, on_fail=Any, **kwargs) -> Any:
        raise NotImplementedError()

    @abc.abstractmethod
    def expand(self, spec=None, state=None, *, rec=False, chain:list[DootKey]=None, on_fail=Any, locs:DootLocations=None, **kwargs) -> str:
        pass

class DootNonKey(str, DootKey):
    """
      Just a string, not a key. But this lets you call no-ops for key specific methods
    """

    def __repr__(self):
        return "<DootNonKey: {}>".format(str(self))

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        match other:
            case DootKey() | str():
                return str(self) == str(other)
            case _:
                return False

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Uknown DootKey target for within", other)

    @property
    def indirect(self) -> DootKey:
        if not self.is_indirect:
            return DootSimpleKey("{}_".format(super().__str__()))
        return self

    @property
    def is_indirect(self):
        return False

    @property
    def form(self):
        """ Return the key in its use form """
        return str(self)

    def expand(self, spec=None, state=None, *, rec=False, chain:list[DootKey]=None, on_fail=Any, locs:DootLocations=None) -> str:
        return str(self)

    def redirect(self, spec=None) -> DootKey:
        return self

    def to_type(self, spec, state, type_=Any, **kwargs) -> str:
        if type_ != Any or type_ != str:
            raise TypeError("NonKey's can only be strings", self)
        return str(self)

class DootSimpleKey(str, DootKey):
    """
      A Single key with no extras.
      ie: {x}. not {x}{y}, or {x}.blah.
    """

    def __repr__(self):
        return "<DootSimpleKey: {}>".format(str(self))

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        match other:
            case DootKey() | str():
                return str(self) == str(other)
            case _:
                return False

    @property
    def indirect(self):
        if not self.is_indirect:
            return DootSimpleKey("{}_".format(super().__str__()))
        return self

    @property
    def is_indirect(self):
        return str(self).endswith("_")

    @property
    def form(self):
        """ Return the key in its use form """
        return "{{{}}}".format(str(self))

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Uknown DootKey target for within", other)

    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DootKey]=None, on_fail=Any, locs:DootLocations=None) -> str:
        key = self.redirect(spec)
        try:
            return DootFormatter.fmt(key, _spec=spec, _state=state, _rec=rec, _locs=locs, _insist=insist)
        except (KeyError, TypeError) as err:
            if bool(chain):
                return chain[0].expand(spec, state, rec=rec, chain=chain[1:], on_fail=on_fail)
            elif on_fail != Any:
                return on_fail
            else:
                raise err

    def redirect(self, spec=None) -> DootKey:
        """
          If the indirect form of the key is found in the spec, use that as a key instead
        """
        if not spec:
            return self

        match spec.kwargs.get(self.indirect, self):
            case str() as x if x == self.indirect:
                return self
            case str() as x:
                return DootKey.make(x)
            case list() as lst:
                raise TypeError("Key Redirection resulted in a list, use redirect_multi", self)

        return self

    def redirect_multi(self, spec=None) -> list[DootKey]:
        """ redirect an indirect key to a *list* of keys """
        if not spec:
            return [self]

        match spec.kwargs.get(self.indirect, self):
            case str() as x if x == self:
                return [self]
            case str() as x:
                return [DootKey.make(x)]
            case list() as lst:
                return [DootKey.make(x) for x in lst]

        return [self]

    def to_type(self, spec=None, state=None, type_=Any, chain:list[DootKey]=None, on_fail=Any) -> Any:
        target            = self.redirect(spec)
        kwargs            = spec.kwargs if spec else {}
        task_name         = state.get("_task_name", None) if state else None
        if task_name:
            cli           = doot.args.on_fail({}).tasks[str(state.get('_task_name', None))]()
        else:
            cli           = {}

        replacement       = cli.get(target, None)
        if replacement is None and kwargs:
            replacement = kwargs.get(target, None)
        if replacement is None and state:
            replacement = state.get(target, None)

        match replacement:
            case None if bool(chain):
                return chain[0].to_type(spec, state, type_=type_, chain=chain[1:], on_fail=on_fail)
            case None if on_fail != Any and isinstance(on_fail, DootKey):
                return on_fail.to_type(spec, state, type_=type_)
            case None if on_fail != Any:
                return on_fail
            case None if type_ is Any or type_ is None:
                return None
            case _ if type_ is Any:
                return replacement
            case _ if type_ and isinstance(replacement, type_):
                return replacement
            case _:
                raise TypeError("Unexpected Type for replacement", type_, replacement, self)

class DootArgsKey(str, DootKey):
    """ A Key representing the action spec's args """

    def __call__(self, spec, state, **kwargs):
        return self.to_type(spec, state)

    def __repr__(self):
        return "<DootArgsKey>"

    def expand(self, *args, **kwargs):
        raise doot.errors.DootKeyError("Args Key doesn't expand")

    def redirect(self, spec=None):
        raise doot.errors.DootKeyError("Args Key doesn't redirect")

    def to_type(self, spec=None, state=None, *args, **kwargs) -> list:
        return spec.args

class DootKwargsKey(DootArgsKey):
    """ A Key representing all of an action spec's kwargs """

    def __repr__(self):
        return "<DootArgsKey>"

    def to_type(self, spec=None, state=None, *args, **kwargs) -> dict:
        return spec.kwargs


class DootMultiKey(DootKey):
    """ A string or path of multiple keys """

    def __init__(self, val:str|pl.Path):
        self.value : str|pl.Path        = val
        self._keys : set[DootSimpleKey] = set(DootSimpleKey(x) for x in PATTERN.findall(str(val)))

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        match other:
            case DootKey() | str() | pl.Path():
                return str(self) == str(other)
            case _:
                return False

    def keys(self) -> set(DootSimpleKey):
        return self._keys

    @property
    def form(self):
        """ Return the key in its use form """
        return str(self)

    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DootKey]=None, on_fail=Any, locs=None, **kwargs) -> str:
        try:
            return DootFormatter.fmt(self.value, _spec=spec, _state=state, _rec=rec, _insist=insist, _locs=locs)
        except (KeyError, TypeError) as err:
            if bool(chain):
                return chain[0].expand(spec, state, rec=rec, chain=chain[1:], on_fail=on_fail)
            elif on_fail != Any:
                return on_fail
            else:
                raise err

    def within(self, other:str|dict|TomlGuard) -> bool:
        return str(self) in other

    def to_type(self, spec, state, type_=Any, chain:list[DootKey]=None, on_fail=Any) -> Any:
        raise TypeError("Converting a MultiKey to a type doesn't make sense", self)

class DootPathKey(DootMultiKey):
    """ A Multi key that always expands as a path """

    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DootKey]=None, on_fail=Any, locs=None):
        return str(self.to_path(spec, state, chain=chain, on_fail=on_fail, locs=locs))


class DootImportKey(DootSimpleKey):
    """ a key to specify a key is used for importing
    ie: str expands -> DootCodeReferene.from_str -> .try_import
    """
    pass
