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


opt_depfile = {
    'section': 'DB backend',
    'name': 'dep_file',
    'short': '',
    'long': 'db-file',
    'type': str,
    'default': ".doit.db",
    'help': "file used to save successful runs [default: %(default)s]"
}

# dependency file DB backend
opt_backend = {
    'section': 'DB backend',
    'name': 'backend',
    'short': '',
    'long': 'backend',
    'type': str,
    'default': "dbm",
    'help': ("Select dependency file backend. [default: %(default)s]")
}

# dependency file codecs
opt_codec = {
    'section': 'doit core',
    'name': 'codec_cls',
    'short': '',
    'long': '',
    'type': str,
    'default': "json",
    'help': ("Select codec for task's data in database. [default: %(default)s]")
}

opt_check_file_uptodate = {
    'section': 'doit core',
    'name': 'check_file_uptodate',
    'short': '',
    'long': 'check_file_uptodate',
    'type': str,
    'default': 'md5',
    'help': """\
Choose how to check if files have been modified.
Available options [default: %(default)s]:
  'md5': use the md5sum
  'timestamp': use the timestamp
"""
}
################################

def version_tuple(ver_in):
    """convert a version string or tuple into a 3-element tuple with ints
    Any part that is not a number (dev0, a2, b4) will be converted to -1
    """
    result = []
    if isinstance(ver_in, str):
        parts = ver_in.split('.')
    else:
        parts = ver_in
    for rev in parts:
        try:
            result.append(int(rev))
        except ValueError:
            result.append(-1)
    assert len(result) == 3
    return result

class DoitCmdBase(Command):
    """
    subclass must define:
    cmd_options => list of option dictionary (see CmdOption)
    _execute => method, argument names must be option names
    """
    base_options = (opt_depfile, opt_backend, opt_codec,
                    opt_check_file_uptodate)

    def __init__(self, task_loader, cmds=None, **kwargs):
        super(DoitCmdBase, self).__init__(**kwargs)
        self.sel_tasks = None  # selected tasks for command
        self.sel_default_tasks = True  # False if tasks were specified from command line
        self.dep_manager = None
        self.outstream = sys.stdout
        self.loader = task_loader
        self._backends = self.get_backends()


    def get_options(self):
        """from base class - merge base_options, loader_options and cmd_options
        """
        opt_list = (self.base_options + self.loader.cmd_options + self.cmd_options)
        return [CmdOption(opt) for opt in opt_list]


    def _execute(self):  # pragma: no cover
        """to be subclassed - actual command implementation"""
        raise NotImplementedError


    @staticmethod
    def check_minversion(minversion):
        """check if this version of doit satisfy minimum required version
        Minimum version specified by configuration on dodo.
        """
        if minversion:
            if version_tuple(minversion) > version_tuple(version.VERSION):
                msg = ('Please update doit. '
                       'Minimum version required is {required}. '
                       'You are using {actual}. ')
                raise InvalidDodoFile(msg.format(required=minversion,
                                                 actual=version.VERSION))

    def get_checker_cls(self, check_file_uptodate):
        """return checker class to be used by dep_manager"""
        if isinstance(check_file_uptodate, str):
            if check_file_uptodate not in CHECKERS:
                msg = ("No check_file_uptodate named '{}'."
                       " Type '{} help run' to see a list "
                       "of available checkers.").format(
                           check_file_uptodate, self.bin_name)
                raise InvalidCommand(msg)
            return CHECKERS[check_file_uptodate]
        else:
            # user defined class
            return check_file_uptodate

    def get_codec_cls(self, codec):
        """return a class used to encode or decode python-action results"""
        if isinstance(codec, str):
            if codec == 'json':
                return JSONCodec
            else:  # pragma: no cover
                raise NotImplementedError('Implement codec plugin')
        else:
            # user specified class
            return codec


    def get_backends(self):
        """return PluginDict of DB backends, including core and plugins"""
        backend_map = {'dbm': DbmDB, 'json': JsonDB, 'sqlite3': SqliteDB}
        # add plugins
        plugins = PluginDict()
        plugins.add_plugins(self.config, 'BACKEND')
        backend_map.update(plugins.to_dict())

        # set choices, sub-classes might not have this option
        if 'backend' in self.cmdparser:
            choices = {k: getattr(v, 'desc', '') for k, v in backend_map.items()}
            self.cmdparser['backend'].choices = choices

        return backend_map


    def execute(self, params, args):
        """load dodo.py, set attributes and call self._execute

        :param params: instance of cmdparse.DefaultUpdate
        :param args: list of string arguments (containing task names)
        """
        self.loader.setup(params)
        dodo_config = self.loader.load_doit_config()

        # merge config values from dodo.py into params
        params.update_defaults(dodo_config)

        self.check_minversion(params.get('minversion'))

        # set selected tasks for command
        self.sel_default_tasks = len(args) == 0
        self.sel_tasks = args or params.get('default_tasks')

        CmdAction.STRING_FORMAT = params.get('action_string_formatting', 'old')
        if CmdAction.STRING_FORMAT not in ('old', 'both', 'new'):
            raise InvalidDodoFile(
                '`action_string_formatting` must be one of `old`, `both`, `new`')

        # create dep manager
        db_class = self._backends.get(params['backend'])
        checker_cls = self.get_checker_cls(params['check_file_uptodate'])
        codec_cls = self.get_codec_cls(params['codec_cls'])
        # note the command have the responsibility to call dep_manager.close()

        if self.dep_manager is None:
            # dep_manager might have been already set (used on unit-test)
            self.dep_manager = Dependency(
                db_class, params['dep_file'], checker_cls=checker_cls,
                codec_cls=codec_cls)

        # register dependency manager in global registry:
        Globals.dep_manager = self.dep_manager
        # load tasks
        self.task_list = self.loader.load_tasks(cmd=self, pos_args=args)

        # hack to pass parameter into _execute() calls that are not part
        # of command line options
        params['pos_args'] = args
        params['continue_'] = params.get('continue')
        # hack: determine if value came from command line or config
        params['force_verbosity'] = 'verbosity' in params._non_default_keys

        # magic - create dict based on signature of _execute() method.
        # this done so that _execute() have a nice API with name parameters
        # instead of just taking a dict.
        args_name = list(inspect.signature(self._execute).parameters.keys())
        exec_params = dict((n, params[n]) for n in args_name)
        return self._execute(**exec_params)



# helper functions to find list of tasks
