#!/usr/bin/env python3
"""

    originally from bibtexparser
    Useful references:
    http://maverick.inria.fr/~Xavier.Decoret/resources/xdkbibtex/bibtex_summary.html#names
    http://tug.ctan.org/info/bibtex/tamethebeast/ttb_en.pdf

    Break a name into its constituent parts: First, von, Last, and Jr.

    :param string name: a string containing a single name
    :param Boolean strict_mode: whether to use strict mode
    :returns: dictionary of constituent parts
    :raises `customization.InvalidName`: If an invalid name is given and
                                         ``strict_mode = True``.

    In BibTeX, a name can be represented in any of three forms:
        * First von Last
        * von Last, First
        * von Last, Jr, First

    This function attempts to split a given name into its four parts. The
    returned dictionary has keys of ``first``, ``last``, ``von`` and ``jr``.
    Each value is a list of the words making up that part; this may be an empty
    list.  If the input has no non-whitespace characters, a blank dictionary is
    returned.

    It is capable of detecting some errors with the input name. If the
    ``strict_mode`` parameter is ``True``, which is the default, this results in
    a :class:`customization.InvalidName` exception being raised. If it is
    ``False``, the function continues, working around the error as best it can.
    The errors that can be detected are listed below along with the handling
    for non-strict mode:

        * Name finishes with a trailing comma: delete the comma
        * Too many parts (e.g., von Last, Jr, First, Error): merge extra parts
          into First
        * Unterminated opening brace: add closing brace to end of input
        * Unmatched closing brace: add opening brace at start of word

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

import re

class NamingRule:
    """
    A way to split a name into parts
    """
    def __call__(self, text):
        pass

class NameConstituents:
    def __init__(self, text, strict=False):
        self._text = text
        self.rules = []
        # Whitespace characters that can separate words.
        self.whitespace = set(' ~\r\n\t')
        self.strict_mode = strict
        self.honourific = []
        self.first      = []
        self.middle     = []
        self.von        = []
        self.last       = []
        self.jr         = []

        self._sections    = [[]]  # Sections of the name.
        self.loop_text()
        match self._sections:
            case [x]:
                self.handle_name_form_one()
            case _:
                self.handle_name_form_two()


    def loop_text(self):
        # We'll iterate over the input once, dividing it into a list of words for
        # each comma-separated section. We'll also calculate the case of each word
        # as we work.
        # Using an iterator allows us to deal with escapes in a simple manner.
        nameiter = iter(self._text)
        word        = []  # Current word.
        case        = -1  # Case of the current word.
        level       = 0  # Current brace level.
        controlseq  = True  # Are we currently processing a control sequence?
        bracestart  = False  # Will the next character be the first within a brace?
        for char in nameiter:
            match char:
                case '\\': # An escape.
                    escaped = next(nameiter)
                    # BibTeX doesn't allow whitespace escaping. Copy the slash and fall
                    # through to the normal case to handle the whitespace.
                    if escaped in self.whitespace:
                        word.append(char)
                        char = escaped
                    elif bracestart: # Is this the first character in a brace?
                        bracestart  = False
                        controlseq  = escaped.isalpha()
                    # Can we use it to determine the case?
                    elif (case == -1) and escaped.isalpha() and escaped.isupper():
                        case = 1
                    else:
                        case = 0
                    # Copy the escape to the current word and go to the next
                    # character in the input.
                    word.append(char)
                    word.append(escaped)
                    continue
                case '{': # Start of a braced expression.
                    level += 1
                    word.append(char)
                    bracestart = True
                    controlseq = False
                    continue
                case '}': # End of a braced expression.
                    # Check and reduce the level.
                    level = (level - 1) if level else 0
                    if level == 0:
                        word.insert(0, '{')
                    # Update the state, append the character, and move on.
                    controlseq  = False
                    word.append(char)
                    continue
                case ',' if len(self._sections) < 3 and bool(self._sections[-1]): # End of a section.
                    self._sections.append([])
                    continue
                case ',':
                    continue
                case _ if level and controlseq and not char.isalpha(): # Inside a braced expression.
                    bracestart = False
                    controlseq = False # Is this the end of a control sequence?
                case  _ if char in self.whitespace and bool(word): # End of a word.
                    # NB. we know we're not in a brace here due to the previous case.
                    # Don't add empty words due to repeated whitespace.
                    self._sections[-1].append((''.join(word), case))
                    word       = []
                    case       = -1
                    controlseq = False
                case _ if case == -1 and char.isalpha() and char.isupper():
                    word.append(char)
                    case = 1
                case _:
                    word.append(char)
                    case = 0

        while level:
            word.append('}')
            level -= 1

        # Handle the final word.
        if word:
            self._sections[-1].append((''.join(word), case))

        # Get rid of trailing sections.
        while bool(self._sections) and not bool(self._sections[-1]):
            self._sections.pop(-1)


    def handle_name_form_one(self):
        # Form 1: "First von Last"
        assert(len(self._sections) == 1)
        match self._sections[0]:
            case [x]: # One word only: last cannot be empty.
                self.last.append(x)
            case [x, y]: # Two words: must be first and last.
                self.first.append(x)
                self.last.append(y)
            # case [*xs] if all(x[1] == 0 for x in xs): # Need to use the cases to figure it out.
            #     parts['first'] = xs[:-1]
            #     parts['last']  = xs[-1:]
            case [*xs, last]:
                # case [*(_, 0) as first, *(_, 1) as von, *(_, 0) as last]:
                # First is the longest sequence of words starting with uppercase
                # that is not the whole string. von is then the longest sequence
                # whose last word starts with lowercase that is not the whole
                # string. Last is the rest. NB., this means last cannot be empty.
                # At least one lowercase letter.
                # Index from end of list of first and last lowercase word.
                # Pull the parts out.
                self.first += [] #first
                self.von   += [] #von
                self.last  += [] #last

    def handle_name_form_two(self):
        # Form 2 ("von Last, First") or 3 ("von Last, jr, First")
        # As long as there is content in the first name partition, use it as-is.
        first = self._sections[-1]
        self.first += first

        # And again with the jr part.
        if len(self._sections) == 3:
            self.jr += self._sections[-2]

        # Last name cannot be empty; if there is only one word in the first
        # partition, we have to use it for the last name.
        match self._sections[0]:
            case [x]:
                self.last.append(x)
            case [*xs, last]:
                # case [*(_, 1) as von, *(_, 0) as last]:
                # At least one lowercase: von is the longest sequence of whitespace
                # separated words whose last word does not start with an uppercase
                # word, and last is the rest.
                self.von  += [] #von
                self.last += [] #last
            case [*last]:
                self.last += last

    # Done.
