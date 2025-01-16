"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import os
import pathlib as pl
import re
import sys
import time
import types
import typing
from importlib.metadata import EntryPoint
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import jgdv.cli
import sh
from jgdv import Maybe
from jgdv.cli.param_spec import LiteralParam, ParamSpec
from jgdv.logging import JGDVLogConfig
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import (Command_i, CommandLoader_p, Job_i, Overlord_p,
                            Task_i, TaskLoader_p)
from doot._abstract.loader import Loader_p
from doot.errors import InvalidConfigError, ParseError
from doot.loaders.cmd_loader import DootCommandLoader
from doot.loaders.plugin_loader import DootPluginLoader
from doot.loaders.task_loader import DootTaskLoader
from doot.mixins.param_spec import ParamSpecMaker_m
from doot.utils.plugin_selector import plugin_selector

# ##-- end 1st party imports

##-- logging
logging    = logmod.getLogger(__name__)
printer    = doot.subprinter()
header_l   = doot.subprinter("header")
setup_l    = doot.subprinter("setup")
help_l     = doot.subprinter("help")
shutdown_l = doot.subprinter("shutdown")
##-- end logging

##-- type aliases
type DootError                         = doot.errors.DootError
type DataSource                        = dict|ChainGuard
type LoaderDict                        = dict[str, Loader_p]

##-- end type aliases

env                                    = os.environ
plugin_loader_key  : Final[str]        = doot.constants.entrypoints.DEFAULT_PLUGIN_LOADER_KEY
command_loader_key : Final[str]        = doot.constants.entrypoints.DEFAULT_COMMAND_LOADER_KEY
task_loader_key    : Final[str]        = doot.constants.entrypoints.DEFAULT_TASK_LOADER_KEY
announce_voice     : Final[str]        = doot.constants.misc.ANNOUNCE_VOICE
version_template   : Final[str]        = doot.constants.printer.version_template

HEADER_MSG         : Final[str]        = doot.constants.printer.doot_header

preferred_cmd_loader                   = doot.config.on_fail("default").startup.loaders.command()
preferred_task_loader                  = doot.config.on_fail("default").startup.loaders.task()
preferred_parser                       = doot.config.on_fail("default").startup.loaders.parser()
empty_call_cmd                         = doot.config.on_fail("list").startup.empty_cmd()
implicit_task_cmd                      = doot.config.on_fail("run").startup.implicit_task_cmd()

DEFAULT_FILENAMES : Final[tuple[*str]] = ("doot.toml", "pyproject.toml")

@doot.check_protocol
class DootOverlord(ParamSpecMaker_m, Overlord_p):
    """
    Main control point for doot.
    prefers passed in loaders, then plugins it finds.

    default cmds are provided by the cmd loader
    """
    _help = ["A Toml Specified Task Runner"]

    @staticmethod
    def print_version() -> None:
        """ print doot version (includes path location) """
        print("Doot Version: %s", doot.__version__)
        print("lib @", pl.Path(__file__).resolve().parent)

    def __init__(self, *, loaders:Maybe[LoaderDict]=None,
                 config_filenames:tuple=DEFAULT_FILENAMES,
                 extra_config:Maybe[DataSource]=None,
                 args:Maybe[list]=None,
                 log_config:Maybe[JGDVLogConfig]=None):
        self.args                                     = args or sys.argv[:]
        self.BIN_NAME                                 = self.args[0].split('/')[-1]
        self.prog_name                                = "doot"
        self.loaders                                  = loaders or {}
        self.log_config                               = log_config

        self.plugins      : Maybe[ChainGuard]         = None
        self.cmds         : Maybe[ChainGuard]         = None
        self.tasks        : Maybe[ChainGuard]         = None
        self.current_cmd  : Command_i                 = None

        self._errored     : Maybe[DootError]          = None
        self._current_cmd : Maybe[str]                = None
        self._extra_config                            = extra_config

    def __call__(self, cmd:Maybe[str]=None) -> int:
        return self.run_doot(cmd)

    @property
    def param_specs(self) -> list[ParamSpec]:
        return [
            LiteralParam(name=self.prog_name),
            self.build_param(name="version" , prefix="--", type=bool),
            self.build_param(name="help"    , prefix="--", type=bool),
            self.build_param(name="verbose" , prefix="--", type=bool),
            self.build_param(name="debug",    prefix="--", type=bool),
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

    def setup(self) -> None:
        logging.info("---- Initialising Overlord")
        self._load_plugins(self._extra_config)
        self._load_commands(self._extra_config)
        self._load_tasks(self._extra_config)
        self._parse_args()
        logging.info("---- Core Overlord Initialisation complete")

    def _load_plugins(self, extra_config:Maybe[dict|ChainGuard]=None) -> None:
        """ Use a plugin loader to find all applicable `importlib.EntryPoint`s  """
        try:
            self.plugin_loader    = self.loaders.get(plugin_loader_key, DootPluginLoader())
            self.plugin_loader.setup(extra_config)
            self.plugins : ChainGuard = self.plugin_loader.load()
            doot._load_aliases(data=self.plugins)
        except doot.errors.PluginError as err:
            shutdown_l.error("Plugins Not Loaded Due to Error: %s", err)
            self.plugins = ChainGuard()

    def _load_commands(self, extra_config:Maybe[dict|ChainGuard]=None) -> None:
        """ Select Commands from the discovered plugins """
        self.cmd_loader = plugin_selector(self.loaders.get(command_loader_key, None) or self.plugins.on_fail([], list).command_loader(),
                                          target=preferred_cmd_loader,
                                          fallback=DootCommandLoader)()

        match self.cmd_loader:
            case None:
                raise TypeError("Command Loader is not initialised")
            case Loader_p():
                try:
                    self.cmd_loader.setup(self.plugins, extra_config)
                    self.cmds = self.cmd_loader.load()
                except doot.errors.PluginError as err:
                    shutdown_l.error("Commands Not Loaded due to Error: %s", err)
                    self.cmds = ChainGuard()
            case _:
                raise TypeError("Unrecognized loader type", self.cmd_loader)

    def _load_tasks(self, extra_config:Maybe[dict|ChainGuard]=None) -> None:
        """ Load task entry points """
        self.task_loader = plugin_selector(self.loaders.get(task_loader_key, None) or self.plugins.on_fail([], list).task_loader(),
                                           target=preferred_task_loader,
                                           fallback=DootTaskLoader)()

        match self.task_loader:
            case None:
                raise TypeError("Task Loader is not initialised")
            case Loader_p():
                self.task_loader.setup(self.plugins, extra_config)
                self.tasks = self.task_loader.load()
            case _:
                raise TypeError("Unrecognised loader type", self.task_loader)

    def _parse_args(self, args:Maybe[list[str]]=None) -> None:
        """ use the found task and command arguments to make sense of sys.argv """
        ctor = plugin_selector(self.loaders.get("parser", None) or self.plugins.on_fail([], list).parser(),
            target=preferred_parser,
            fallback=None,
            )

        match ctor:
            case None:
                self.parser = jgdv.cli.ParseMachine()
            case type() if isinstance((p:=ctor()), jgdv.cli.ArgParser_p):
                self.parser = jgdv.cli.ParseMachine(parser=p)
            case _:
                raise TypeError("Improper argparser specified", self.arg_parser)

        try:
            cli_args = self.parser(
                args or self.args[1:],
                head_specs=self.param_specs,
                cmds=list(self.cmds.values()),
                # Associate tasks with the run cmd
                subcmds=[("run",x) for x in self.tasks.values()],
            )
        except jgdv.cli.errors.HeadParseError as err:
            raise doot.errors.FrontendError("Doot Head Failed to Parse", err) from err
        except jgdv.cli.errors.CmdParseError as err:
            raise doot.errors.FrontendError("Unrecognised Command Called", err) from err
        except jgdv.cli.errors.SubCmdParseError as err:
            raise doot.errors.FrontendError("Unrecognised Task Called", err.args[1]) from err
        except jgdv.cli.errors.ArgParseError as err:
            raise doot.errors.FrontendError("Parsing arguments for command/task failed", err) from err
        except jgdv.cli.ParseError as err:
            raise doot.errors.ParseError("Failed to Parse provided cli args", err) from err

        doot.args = ChainGuard(cli_args)

    def run_doot(self, cmd:Maybe[str]=None) -> int:
        """ The main run logic of the overlord """
        if not doot.args.on_fail(False).cmd.args.suppress_header():
            header_l.user(HEADER_MSG, extra={"colour": "green"})

        if doot.args.on_fail(False).head.args.debug():
            printer.user("Pausing for debugging")
            breakpoint()
            pass

        # perform head args
        if self._handle_cli_args():
            return

        # Do the cmd
        try:
            logging.info("---- Overlord Calling: %s", cmd or doot.args.on_fail("Unknown").cmd.name())
            cmd = self._get_cmd(cmd)
            cmd(self.tasks, self.plugins)
        except doot.errors.DootError as err:
            self._errored = err
            raise err
        else:
            logging.info("---- Overlord Cmd Call Complete")
            return 0

    def _handle_cli_args(self) -> bool:
        """ Overlord specific cli arg responses. modify verbosity,
          print version, and help.

          return True to end doot early
        """
        if doot.args.on_fail(False).head.args.verbose() and self.log_config:
            logging.info("Switching to Verbose Output")
            self.log_config.set_level("NOTSET")

        logging.info("CLI Args: %s", doot.args._table())
        logging.info("Plugins: %s", dict(self.plugins).keys())
        logging.info("Tasks: %s", self.tasks.keys())

        if doot.args.on_fail(False).head.args.version():
            help_l.user(version_template, doot.__version__)
            return True

        if doot.args.on_fail(False).head.args.help():
            help_l.user(self.help)
            return True

        return False

    def _get_cmd(self, cmd=None) -> Callable:
        if self.current_cmd is not None:
            return self.current_cmd

        target = cmd or doot.args.on_fail(implicit_task_cmd).cmd.name()

        match self.cmds.get(target, None):
            case None if bool(doot.args.sub):
                self.current_cmd = self.cmds.get(implicit_task_cmd, None)
            case None if target.startswith("_") and target.endswith("_"):
                self.current_cmd = self.cmds.get(empty_call_cmd, None)
            case x:
                self.current_cmd = x

        if self.current_cmd is None:
            self._errored = jgdv.cli.ParseError("Specified Command Couldn't be Found: %s", target)
            raise self._errored

        return self.current_cmd

    def shutdown(self) -> None:
        """ Doot has finished normally, so report on what was done """
        logging.info("Shutting Down Overlord")
        if self.current_cmd is not None and hasattr(self.current_cmd, "shutdown"):
            self.current_cmd.shutdown(self._errored, self.tasks, self.plugins)

        self._record_defaulted_config_values()

        shutdown_l.user("")
        match self._errored:
            case doot.errors.DootError() as err:
                msg = doot.config.on_fail("Errored").shutdown.notify.fail_msg()
                shutdown_l.user("---- %s ----", msg)
                shutdown_l.error(err)
                self._announce_exit(msg)
            case None:
                msg = doot.config.on_fail("").shutdown.notify.success_msg()
                self._announce_exit(msg)
                shutdown_l.user(msg)

        shutdown_l.user("---- Dooted ----")

    def _announce_exit(self, message:str):
        if not doot.config.on_fail(False).shutdown.notify.say_on_exit():
            return

        match sys.platform:
            case _ if "PRE_COMMIT" in env:
                return
            case "linux":
                sh.espeak(message)
            case "darwin":
                sh.say("-v", "Moira", "-r", "50", message)

    def _record_defaulted_config_values(self):
        if not doot.config.on_fail(False).shutdown.write_defaulted_values():
            return

        defaulted_file = doot.config.on_fail("{logs}/.doot_defaults.toml", pl.Path).shutdown.defaulted_values.path()
        expanded_path = doot.locs.Current[defaulted_file]
        if not expanded_path.parent.exists():
            shutdown_l.error("Couldn't log defaulted config values to: %s", expanded_path)
            return

        defaulted_toml = ChainGuard.report_defaulted()
        with pl.Path(expanded_path).open('w') as f:
            f.write("# default values used:\n")
            f.write("\n".join(defaulted_toml) + "\n\n")
