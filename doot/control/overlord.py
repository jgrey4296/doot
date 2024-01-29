"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import sys
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)

# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

from importlib.metadata import EntryPoint

import doot
import doot.errors
import doot.constants
import tomlguard
from doot._abstract import (ArgParser_i, Command_i, CommandLoader_p,
                            Overlord_p, Task_i, Job_i, TaskLoader_p)

from doot.utils.plugin_selector import plugin_selector
from doot.errors import DootInvalidConfig, DootParseError
from doot.loaders.cmd_loader import DootCommandLoader
from doot.loaders.plugin_loader import DootPluginLoader
from doot.loaders.task_loader import DootTaskLoader
from doot.parsers.flexible import DootFlexibleParser

plugin_loader_key  : Final = doot.constants.DEFAULT_PLUGIN_LOADER_KEY
command_loader_key : Final = doot.constants.DEFAULT_COMMAND_LOADER_KEY
task_loader_key    : Final = doot.constants.DEFAULT_TASK_LOADER_KEY

preferred_cmd_loader  = doot.config.on_fail("default").settings.general.loaders.command()
preferred_task_loader = doot.config.on_fail("default").settings.general.loaders.task()
preferred_parser      = doot.config.on_fail("default").settings.general.loaders.parser()

defaulted_file = doot.config.on_fail(pl.Path(".doot_defaults.toml"), pl.Path).report.defaulted_file(pl.Path)

@doot.check_protocol
class DootOverlord(Overlord_p):
    """
    Main control point for doot.
    prefers passed in loaders, then plugins it finds.

    default cmds are provided by the cmd loader
    """
    _help = ["An opinionated rewrite of Doit"]

    @staticmethod
    def print_version():
        """ print doot version (includes path location) """
        print("Doot Version: %s", doot.__version__)
        print("lib @", os.path.dirname(os.path.abspath(__file__)))

    def __init__(self, *, loaders:dict[str, Loader_i]=None, config_filenames:tuple=('doot.toml', 'pyproject.toml'), extra_config:dict|TomlGuard=None, args:list=None, log_config:None|DootLogConfig=None):
        logging.debug("Initialising Overlord")
        self.args                                = args or sys.argv[:]
        self.BIN_NAME                            = self.args[0].split('/')[-1]
        self.loaders                             = loaders or dict()
        self.log_config                          = log_config

        self.plugins      : None|TomlGuard       = None
        self.cmds         : None|TomlGuard       = None
        self.tasks        : None|TomlGuard       = None
        self.current_cmd  : Command_i            = None

        self._errored     : None|DootError       = None
        self._current_cmd : None|str             = None

        self._load_plugins(extra_config)
        self._load_commands(extra_config)
        self._load_tasks(extra_config)
        self._parse_args()
        logging.debug("Core Overlord Initialisation complete")

    @property
    def param_specs(self) -> list[DootParamSpec]:
        return [
           self.make_param(name="version" , prefix="--"),
           self.make_param(name="help"    , prefix="--"),
           self.make_param(name="verbose" , prefix="--"),
           self.make_param(name="debug",    prefix="--")
        ]

    @property
    def help(self) -> str:
        help_lines = ["", f"Doot v{doot.__version__}", ""]
        help_lines += self._help

        params = self.param_specs
        if bool(params):
            help_lines += ["", "Params:"]
            help_lines += sorted(str(x) for x in self.param_specs)

        help_lines.append("")
        help_lines.append("Commands: ")
        help_lines += sorted(x.helpline for x in self.cmds.values())

        return "\n".join(help_lines)

    def _load_plugins(self, extra_config:dict|TomlGuard=None):
        """ Use a plugin loader to find all applicable `importlib.EntryPoint`s  """
        try:
            self.plugin_loader    = self.loaders.get(plugin_loader_key, DootPluginLoader())
            self.plugin_loader.setup(extra_config)
            self.plugins : TomlGuard = self.plugin_loader.load()
        except doot.errors.DootPluginError as err:
            printer.warning("Plugins Not Loaded Due to Error: %s", err)
            self.plugins = tomlguard.TomlGuard()

    def _load_commands(self, extra_config):
        """ Select Commands from the discovered plugins """
        self.cmd_loader = plugin_selector(self.loaders.get(command_loader_key, None) or self.plugins.on_fail([], list).command_loader(),
                                        target=preferred_cmd_loader,
                                        fallback=DootCommandLoader)()

        if self.cmd_loader is None:
            raise TypeError("Command Loader is not initialised")
        if not isinstance(self.cmd_loader, CommandLoader_p):
            raise TypeError("Attempted to use a non-CommandLoader_p as a CommandLoader: ", self.cmd_loader)

        try:
            self.cmd_loader.setup(self.plugins, extra_config)
            self.cmds = self.cmd_loader.load()
        except doot.errors.DootPluginError as err:
            printer.warning("Commands Not Loaded due to Error: %s", err)
            self.cmds = tomlguard.TomlGuard()

    def _load_tasks(self, extra_config):
        """ Load task entry points """

        self.task_loader = plugin_selector(self.loaders.get(task_loader_key, None) or self.plugins.on_fail([], list).task_loader(),
                                            target=preferred_task_loader,
                                            fallback=DootTaskLoader)()

        if self.task_loader is None:
            raise TypeError("Task Loader is not initialised")
        if not isinstance(self.task_loader, TaskLoader_p):
            raise TypeError("Attempted to use a non-Commandloader_i as a CommandLoader: ", self.cmd_loader)

        self.task_loader.setup(self.plugins, extra_config)
        self.tasks = self.task_loader.load()

    def _parse_args(self, args=None):
        """ use the found task and command arguments to make sense of sys.argv """
        self.parser = plugin_selector(self.loaders.get("parser", None) or self.plugins.on_fail([], list).parser(),
                                     target=preferred_parser,
                                     fallback=DootFlexibleParser)()

        if not isinstance(self.parser, ArgParser_i):
            raise TypeError("Improper argparser specified: ", self.arg_parser)

        doot.args = self.parser.parse(args or self.args, doot_specs=self.param_specs, cmds=self.cmds, tasks=self.tasks)

    def _cli_arg_response(self) -> bool:
        """ Overlord specific cli arg responses. modify verbosity,
          print version, and help.
        """
        if doot.args.on_fail(False).head.args.verbose() and self.log_config:
            printer.info("Switching to Verbose Output")
            self.log_config.set_level("NOTSET")
            pass

        logging.info("CLI Args: %s", doot.args._table())
        logging.info("Plugins: %s", dict(self.plugins))
        logging.info("Tasks: %s", self.tasks.keys())

        if doot.args.on_fail(False).head.args.version():
            printer.info("\n\n----- Doot Version: %s\n\n", doot.__version__)
            return True

        if doot.args.on_fail(False).head.args.help():
            printer.info(self.help)

            return True

        return False

    def __call__(self, cmd=None):

        if not doot.args.on_fail((None,)).cmd.args.suppress_header():
            printer.info("----------------------------------------------", extra={"colour" : "green"})
            printer.info("-------------------- Doot --------------------", extra={"colour" : "yellow"})
            printer.info("----------------------------------------------", extra={"colour": "green"})

        if doot.args.on_fail(False).head.args.debug():
            breakpoint()
            pass

        # perform head args
        if self._cli_arg_response():
            return

        # Do the cmd
        logging.info("Overlord Calling: %s", cmd or doot.args.on_fail("Unknown").cmd.name())
        try:
            cmd = self._get_cmd(cmd)
            cmd(self.tasks, self.plugins)
        except doot.errors.DootError as err:
            self._errored = err
            raise err from err

    def _get_cmd(self, cmd=None):
        if self.current_cmd is not None:
            return self.current_cmd

        target = cmd or doot.args.on_fail(doot.constants.DEFAULT_CLI_CMD).cmd.name()

        self.current_cmd = self.cmds.get(target, None)
        if self.current_cmd is None:
            self._errored = DootParseError("Specified Command Couldn't be Found: %s", target)
            raise self._errored

        return self.current_cmd



    def shutdown(self):
        """ Doot has finished normally, so report on what was done """
        if self.current_cmd is not None and hasattr(self.current_cmd, "shutdown"):
            self.current_cmd.shutdown(self._errored, self.tasks, self.plugins)

        match self._errored:
            case doot.errors.DootError():
                pass
            case None:
                logging.info("Shutting Doot Down Normally, reporting defaulted tomlguard values")
                defaulted_toml = tomlguard.TomlGuard.report_defaulted()

                with open(defaulted_file, 'w') as f:
                    f.write("# default values used:\n")
                    f.write("\n".join(defaulted_toml) + "\n\n")
                    # f.write("[.directories]\n")
                    # f.write("\n".join(defaulted_locs))
