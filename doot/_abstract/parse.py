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


class CmdOption_i:

    _boolean_states = {
        '1': True, 'yes': True, 'true': True, 'on': True,
        '0': False, 'no': False, 'false': False, 'off': False,
    }

    def __init__(self, opt_dict):
        opt_dict = opt_dict.copy()
        for field in ('name', 'default',):
            if field not in opt_dict:
                msg = "CmdOption dict %r missing required property '%s'"
                raise CmdParseError(msg % (opt_dict, field))

        self.name    = opt_dict.pop('name')
        self.section = opt_dict.pop('section', '')
        self.type    = opt_dict.pop('type', str)
        self.set_default(opt_dict.pop('default'))
        self.short   = opt_dict.pop('short', '')
        self.long    = opt_dict.pop('long', '')
        self.inverse = opt_dict.pop('inverse', '')
        self.choices = dict(opt_dict.pop('choices', []))
        self.help    = opt_dict.pop('help', '')
        self.metavar = opt_dict.pop('metavar', 'ARG')
        self.env_var = opt_dict.pop('env_var', None)

    def set_default(self, val):
        pass

    def validate_choice(self, given_value):
        pass

    def str2boolean(self, str_val):
        """convert string to boolean"""
        try:
            return self._boolean_states[str_val.lower()]
        except Exception:
            raise ValueError('Not a boolean: {}'.format(str_val))

    def str2type(self, str_val):
        """convert string value to option type value"""
        try:
            # no conversion if value is not a string
            if not isinstance(str_val, str):
                val = str_val
            elif self.type is bool:
                val = self.str2boolean(str_val)
            elif self.type is list:
                parts = [p.strip() for p in str_val.split(',')]
                val = [p for p in parts if p]  # remove empty strings
            else:
                val = self.type(str_val)
        except ValueError as exception:
            msg = (f"Error parsing parameter '{self.name}' {self.type}.\n"
                   f"{exception}\n")
            raise CmdParseError(msg)

        if self.choices:
            self.validate_choice(val)
        return val


    @staticmethod
    def _print_2_columns(col1, col2):
        """print using a 2-columns format """
        column1_len = 24
        column2_start = 28
        left = (col1).ljust(column1_len)
        right = col2.replace('\n', '\n' + column2_start * ' ')
        return "  %s  %s" % (left, right)

    def help_param(self):
        """return string of option's short and long name
        i.e.:   -f ARG, --file=ARG
        """
        pass

    def help_choices(self):
        """return string with help for option choices"""
        pass

    def help_doc(self):
        """return list of string of option's help doc

        Note this is used only to display help on tasks.
        For commands a better and more complete version is used.
        see cmd_base:Command.help
        """
        pass


class CmdParse_i:
    """Process string with command options

    @ivar options: (list - CmdOption)
    """
    _type = "Command"

    def __init__(self, options):
        self._options = OrderedDict((o.name, o) for o in options)

    def __contains__(self, key):
        pass

    def __getitem__(self, key):
        pass


    def get_short(self):
        """return string with short options for getopt"""
        pass

    def get_long(self):
        """return list with long options for getopt"""
        pass

    def get_option(self, opt_str):
        """return tuple
            - CmdOption from matching opt_str. or None
            - (bool) matched inverse
        """
        pass

    def overwrite_defaults(self, new_defaults):
        """overwrite self.options default values

        This values typically come from an INI file
        """
        pass

    def parse(self, in_args):
        """parse arguments into options(params) and positional arguments

        Also get values from shell ENV.

        Returned params is a `DefaultUpdate` type and includes
        an item for every option.

        @param in_args (list - string): typically sys.argv[1:]
        @return params, args
             params(dict): params contain the actual values from the options.
                           where the key is the name of the option.
             pos_args (list - string): positional arguments
        """
        pass
