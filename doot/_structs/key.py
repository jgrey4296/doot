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
printer = logmod.getLogger("doot._printer")
##-- end logging

import decorator
import abc
import string
from tomlguard import TomlGuard
import doot
import doot.errors
from doot._structs.code_ref import DootCodeReference
from doot._abstract.structs import SpecStruct_p
from doot.utils.chain_get import DootKeyGetter
from doot.utils.decorators import DootDecorator, DecorationUtils

KEY_PATTERN                                = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                         = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                          = doot.constants.patterns.STATE_TASK_NAME_K

PATTERN        : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN   : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"

class KeyDecorator:
    """ Decorators for actions
    KeyDecorator is accessible as DootKey.kwrap

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
        """ mark an action as using spec.args """
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

class DootFormatter(string.Formatter):
    """
      A Formatter for expanding arguments based on action spec kwargs, and task state, and cli args
    """
    _fmt                = None

    SPEC   : Final[str] = "_spec"
    INSIST : Final[str] = "_insist"
    STATE  : Final[str] = "_state"
    LOCS   : Final[str] = "_locs"
    REC    : Final[str] = "_rec"

    @staticmethod
    def fmt(fmt:str|DootKey|pl.Path, /, *args, **kwargs) -> str:
        if not DootFormatter._fmt:
            DootFormatter._fmt = DootFormatter()

        return DootFormatter._fmt.format(fmt, *args, **kwargs)

    def format(self, fmt:str|DootKey|pl.Path, /, *args, **kwargs) -> str:
        """ expand and coerce keys """
        self._depth = 0
        match kwargs.get(self.SPEC, None):
            case None:
                kwargs['_spec'] = {}
            case SpecStruct_p():
                kwargs['_spec'] = kwargs[self.SPEC].params
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
        """ lowest level handling of keys being expanded """
        logging.debug("Expanding: %s", key)
        if isinstance(key, int):
            return args[key]

        insist                = kwargs.get(self.INSIST, False)
        spec  : dict          = kwargs.get(self.SPEC, None) or {}
        state : dict          = kwargs.get(self.STATE, None) or {}
        locs  : DootLocations = kwargs.get(self.LOCS,  None)
        depth_check           = self._depth < MAX_KEY_EXPANSIONS
        rec_allowed           = kwargs.get(self.REC, False) and depth_check

        match (replacement:=DootKeyGetter.chained_get(key, spec, state, locs)):
            case None if insist:
                raise KeyError("Key Expansion Not Found")
            case None:
                return DootKey.build(key).form
            case DootKey() if depth_check:
                self._depth += 1
                return self.vformat(replacement.form, args, kwargs)
            case str() if rec_allowed:
                self._depth += 1
                return self.vformat(str(replacement), args, kwargs)
            case str():
                return replacement
            case pl.Path() if depth_check:
                self._depth += 1
                return ftz.reduce(pl.Path.joinpath, map(lambda x: self.vformat(x, args, kwargs), replacement.parts), pl.Path())
            case _:
                return str(replacement)
                # raise TypeError("Replacement Value isn't a string", args, kwargs)

class DootKey(abc.ABC):
    """ A shared, non-functional base class for DootKeys and variants like DootMultiKey.
      Use DootKey.build for constructing keys
      build takes an 'exp_hint' kwarg dict, which can specialize the expansion

      DootSimpleKeys are strings, wrapped in {} when used in toml.
      so DootKey.build("blah") -> DootSimpleKey("blah") -> DootSimpleKey('blah').form =="{blah}" -> [toml] aValue = "{blah}"

      DootMultiKeys are containers of a string `value`, and a list of SimpleKeys the value contains.
      So DootKey.build("{blah}/{bloo}") -> DootMultiKey("{blah}/{bloo}", [DootSimpleKey("blah", DootSimpleKey("bloo")]) -> .form == "{blah}/{bloo}"
    """
    dec   = KeyDecorator
    kwrap = KeyDecorator

    @staticmethod
    def build(s:str|DootKey|pl.Path|dict, *, strict=False, explicit=False, exp_hint:str|dict=None, help=None) -> DootKey:
        """ Make an appropriate DootKey based on input value
          Can only create MultiKeys if strict = False,
          if explicit, only keys wrapped in {} are made, everything else is returned untouched
          if strict, then only simple keys can be returned
        """
        # TODO annotate with 'help'
        # TODO store expansion args on build
        match exp_hint:
            case "path":
                is_path = True
            case {"expansion": "path"}:
                is_path = True
            case _:
                is_path = False
        result = s
        match s:
            case { "path": x }:
                result = DootPathMultiKey(x)
                exp_hint = "path"
            case pl.Path():
                result = DootPathMultiKey(s)
                exp_hint = "path"
            case DootSimpleKey() if strict:
                result = s
            case DootKey():
                result = s
            case str() if not (s_keys := PATTERN.findall(s)) and not explicit and not is_path:
                result = DootSimpleKey(s)
            case str() if is_path and not bool(s_keys):
                result = DootPathSimpleKey(s)
            case str() if is_path and len(s_keys) == 1 and s_keys[0] == s[1:-1]:
                result = DootPathSimpleKey(s[1:-1])
            case str() if is_path and len(s_keys) > 1:
                result = DootPathMultiKey(s)
            case str() if not s_keys and explicit:
                result = DootNonKey(s)
            case str() if len(s_keys) == 1 and s_keys[0] == s[1:-1]:
                result = DootSimpleKey(s[1:-1])
            case str() if not strict:
                result = DootMultiKey(s)
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
            case {"expansion": "coderef"}:
                return self.to_coderef(spec, state)
            case x:
                raise doot.errors.DootKeyError("Key Called with Bad Key Expansion Type", self, x)

    @property
    def form(self) -> str:
        return str(self)

    @property
    def direct(self):
        return str(self).removesuffix("_")

    @property
    def is_indirect(self) -> bool:
        return False

    def redirect(self, spec=None) -> DootKey:
        return self

    def to_path(self, spec=None, state=None, chain:list[DootKey]=None, locs:DootLocations=None, on_fail:None|str|pl.Path|DootKey=Any, symlinks=False) -> pl.Path:
        """
          Convert a key to an absolute path, using registered locations

          The Process is:
          1) redirect the given key if necessary
          2) Expand each part of the keypath, using DootFormatter
          3) normalize it

          If necessary, a fallback chain, and on_fail value can be provided
        """
        locs                 = locs or doot.locs
        key : pl.Path        = pl.Path(self.redirect(spec).form)

        try:
            expanded         : list       = [DootFormatter.fmt(x, _spec=spec, _state=state, _rec=True, _locs=locs) for x in key.parts]
            expanded_as_path : pl.Path    = pl.Path().joinpath(*expanded) # allows ("a", "b/c") -> "a/b/c"

            if bool(matches:=PATTERN.findall(str(expanded_as_path))):
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

    def basic(self, spec:SpecStruct_p, state, locs=None):
        """ the most basic expansion of a key """
        kwargs = spec.params
        return DootKeyGetter.chained_get(str(self), kwargs, state, locs or doot.locs)

    @abc.abstractmethod
    def to_type(self, spec, state, type_=Any, chain:list[DootKey]=None, on_fail=Any, **kwargs) -> Any:
        raise NotImplementedError()

    @abc.abstractmethod
    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DootKey]=None, on_fail=Any, locs:DootLocations=None, **kwargs) -> str:
        pass

    def to_coderef(self, spec:None|SpecStruct_p, state) -> None|DootCodeReference:
        match spec:
            case SpecStruct_p():
                kwargs = spec.params
            case None:
                kwargs = {}

        redir = self.redirect(spec)

        if redir not in kwargs and redir not in state:
            return None
        try:
            expanded = self.expand(spec, state)
            ref = DootCodeReference.build(expanded)
            return ref
        except doot.errors.DootError:
            return None

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

    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DootKey]=None, on_fail=Any, locs:DootLocations=None, **kwargs) -> str:
        return str(self)

    def redirect(self, spec=None) -> DootKey:
        return self

    def to_type(self, spec, state, type_=Any, **kwargs) -> str:
        if type_ not in [Any, str]:
            raise TypeError("NonKey's can only be strings", self, type_)
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
        """ Return the key in its use form, ie: wrapped in braces """
        return "{{{}}}".format(str(self))

    def within(self, other:str|dict|TomlGuard) -> bool:
        match other:
            case str():
                return self.form in other
            case dict() | TomlGuard():
                return self in other
            case _:
                raise TypeError("Uknown DootKey target for within", other)

    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DootKey]=None, on_fail=Any, locs:DootLocations=None, **kwargs) -> str:
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

    def redirect(self, spec:None|SpecStruct_p=None) -> DootKey:
        """
          If the indirect form of the key is found in the spec, use that as a key instead
        """
        if not spec:
            return self

        match spec:
            case SpecStruct_p():
                kwargs = spec.params
            case None:
                kwargs = {}

        match kwargs.get(self.indirect, self):
            case str() as x if x == self.indirect:
                return self
            case str() as x:
                return DootKey.build(x)
            case list() as lst:
                raise TypeError("Key Redirection resulted in a list, use redirect_multi", self)

        return self

    def redirect_multi(self, spec:None|SpecStruct_p=None) -> list[DootKey]:
        """ redirect an indirect key to a *list* of keys """
        if not spec:
            return [self]

        match spec:
            case SpecStruct_p():
                kwargs = spec.params
            case None:
                kwargs = {}

        match kwargs.get(self.indirect, self):
            case str() as x if x == self:
                return [self]
            case str() as x:
                return [DootKey.build(x)]
            case list() as lst:
                return [DootKey.build(x) for x in lst]

        return [self]

    def to_type(self, spec:None|SpecStruct_p=None, state=None, type_=Any, chain:list[DootKey]=None, on_fail=Any) -> Any:
        target            = self.redirect(spec)

        match spec:
            case SpecStruct_p():
                kwargs = spec.params
            case None:
                kwargs = {}

        task_name = state.get(STATE_TASK_NAME_K, None) if state else None
        match (replacement:=DootKeyGetter.chained_get(target, kwargs, state)):
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
            case None if not any(target in x for x in [kwargs, state]):
                raise KeyError("Key is not available in the state or spec", target)
            case _:
                raise TypeError("Unexpected Type for replacement", type_, replacement, self)

class DootPathSimpleKey(DootSimpleKey):
    """ A Key that always expands as a path """

    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DootKey]=None, on_fail=Any, locs=None, **kwargs):
        return str(self.to_path(spec, state, chain=chain, on_fail=on_fail, locs=locs))

    def __repr__(self):
        return "<DootPathSimpleKey: {}>".format(str(self))

    def __call__(self, spec, state):
        """ Expand the key using the registered expansion hint """
        match getattr(self, EXPANSION_HINT, False):
            case False:
                return self.to_path(spec, state)
            case {"expansion": "str", "kwargs": kwargs}:
                return self.expand(spec, state, **kwargs)
            case {"expansion": "path", "kwargs": kwargs}:
                return self.to_path(spec, state, **kwargs)
            case {"expansion": "redirect"}:
                return self.redirect(spec)
            case {"expansion": "redirect_multi"}:
                return self.redirect_multi(spec)
            case x:
                raise doot.errors.DootKeyError("Key Called with Bad Key Expansion Type", self, x)

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

    def to_type(self, spec:None|SpecStruct_p=None, state=None, *args, **kwargs) -> dict:
        match spec:
            case SpecStruct_p():
                return spec.params
            case None:
                return {}

class DootMultiKey(DootKey):
    """ A string or path of multiple keys """

    def __init__(self, val:str|pl.Path):
        self.value : str|pl.Path        = val
        self._keys : set[DootSimpleKey] = set(DootSimpleKey(x) for x in PATTERN.findall(str(val)))

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "<DootMultiKey: {}>".format(str(self))

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
        raise TypeError("Converting a MultiKey to a type doesn't build sense", self)

class DootPathMultiKey(DootMultiKey):
    """ A MultiKey that always expands as a path """

    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DootKey]=None, on_fail=Any, locs=None, **kwargs):
        return str(self.to_path(spec, state, chain=chain, on_fail=on_fail, locs=locs))

    def __repr__(self):
        return "<DootPathMultiKey: {}>".format(str(self))

    def __call__(self, spec, state):
        """ Expand the key using the registered expansion hint """
        match getattr(self, EXPANSION_HINT, False):
            case False:
                return self.to_path(spec, state)
            case {"expansion": "str", "kwargs": kwargs}:
                return self.expand(spec, state, **kwargs)
            case {"expansion": "path", "kwargs": kwargs}:
                return self.to_path(spec, state, **kwargs)
            case {"expansion": "redirect"}:
                return self.redirect(spec)
            case {"expansion": "redirect_multi"}:
                return self.redirect_multi(spec)
            case x:
                raise doot.errors.DootKeyError("Key Called with Bad Key Expansion Type", self, x)

class DootImportKey(DootSimpleKey):
    """ a key to specify a key is used for importing
    ie: str expands -> DootCodeReference.build -> .try_import
    """
    pass
