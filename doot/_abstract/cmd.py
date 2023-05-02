import inspect
import sys
from collections import deque
from collections import defaultdict
import textwrap

from . import version
from .cmdparse import CmdOption, CmdParse
from .exceptions import InvalidCommand, InvalidDodoFile
from .dependency import CHECKERS, DbmDB, JsonDB, SqliteDB, Dependency, JSONCodec
from .action import CmdAction
from .plugin import PluginDict
from . import loader

class DootCommand_i:
    """
    holds command information and performs it
    """

    # if not specified uses the class name
    name = None

    # doc attributes, should be sub-classed
    doc_purpose     = ''
    doc_usage       = ''
    doc_description = None  # None value will completely omit line from doc

    # sequence of dicts
    cmd_options = tuple()

    # `execute_tasks` indicates whether this command execute task's actions.
    # This is used by the loader to indicate when delayed task creation
    # should be used.
    execute_tasks = False

    def __init__(self, config=None, bin_name='doot', opt_vals=None, **kwargs):
        self.bin_name = bin_name
        self.name = self.get_name()
        # config includes all option values and plugins
        self.config = config if config else {}
        self._cmdparser = None
        # option values (i.e. loader options)
        self.opt_vals = opt_vals if opt_vals else {}

        # config_vals contains cmd option values
        self.config_vals = {}
        if 'GLOBAL' in self.config:
            self.config_vals.update(self.config['GLOBAL'])
        if self.name in self.config:
            self.config_vals.update(self.config[self.name])

        # Use post-mortem PDB in case of error loading tasks.
        # Only available for `run` command.
        self.pdb = False

    @classmethod
    def get_name(cls):
        """get command name as used from command line"""
        return cls.name or cls.__name__.lower()

    @property
    def cmdparser(self):
        if not self._cmdparser:
            self._cmdparser = CmdParse(self.get_options())
            self._cmdparser.overwrite_defaults(self.config_vals)
        return self._cmdparser

    def parse_args(self, in_args) -> dict:
        return {}

    def get_options(self):
        return [CmdOption(opt) for opt in self.cmd_options]

    def __call__(self, opt_values, pos_args):
        args = self.parse_args(opt_values, pos_args)
        return self._execute(args)

    def _execute(self, args):
        raise NotImplementedError()


    def help(self) -> str:
        return ""
