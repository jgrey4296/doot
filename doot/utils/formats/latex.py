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
# see /opt/anaconda3/envs/bookmark/lib/python3.10/site-packages/pylatexenc/latexencode/_uni2latexmap.py

from pylatexenc.latex2text import LatexNodes2Text
from pylatexenc.latexencode import UnicodeToLatexEncoder, UnicodeToLatexConversionRule, RULE_DICT

latex_to_unicode = LatexNodes2Text()
unicode_to_latex = UnicodeToLatexEncoder(non_ascii_only=False,
                                         replacement_latex_protection="braces", # braces, braces-all, braces-almost-all, none
                                         conversion_rules=[
        UnicodeToLatexConversionRule(RULE_DICT,
                                    {
                                     0x2013 : "--",
                                     0x2014 : "---",
                                     0x0026 : u"\\&",
                                     0x005c : "\\",
                                     0x201c : "``",
                                     0x201d : "''",
                                     0x03A0 : "$\\Pi$",
                                     0x03C0 : "$\\pi$",
                                     0x003C: r'$<$',
                                     0x003E: r'$>$',

                                     0x03B1: '$\\alpha$',
                                     0x03B2: r'$\beta$',
                                     0x03B3: r'$\gamma$',
                                     0x03B4: r'$\delta$',
                                     0x03B5: r'$\varepsilon$',
                                     0x03B6: r'$\zeta$',
                                     0x03B7: r'$\eta$',
                                     0x03B8: r'$\theta$',
                                     0x03B9: r'$\iota$',
                                     0x03BA: r'$\kappa$',
                                     0x03BB: r'$\lambda$',
                                     0x03BC: r'$\mu$',
                                     0x03BD: r'$\nu$',
                                     0x03BE: r'$\xi$',
                                     0x03BF: r'o',
                                     0x03C0: r'$\pi$',
                                     0x03C1: r'$\rho$',
                                     0x03C2: r'$\varsigma$',
                                     0x03C3: r'$\sigma$',
                                     0x03C4: r'$\tau$',
                                     0x03C5: r'$\upsilon$',
                                     0x03C6: r'$\varphi$',
                                     0x03C7: r'$\chi$',
                                     0x03C8: r'$\psi$',
                                     0x03C9: r'$\omega$',

                                     0x03D1: r'$\vartheta$',
                                     0x03D2: r'$\Upsilon$',
                                     0x03D5: r'$\phi$',
                                     0x03D6: r'$\varpi$',
                                     0x03F0: r'$\varkappa$',
                                     0x03F1: r'$\varrho$',
                                     0x03F5: r'$\epsilon$',
                                     0x03F6: r'$\backepsilon$',
                                     }),
        "defaults",
        ])

def to_unicode(entry:str) -> str:
    """
    convert the entry to unicode, removing newlines
    """
    return latex_to_unicode.latex_to_text(entry)

def to_latex(text:str) -> str:
    return unicode_to_latex.unicode_to_latex(text)
