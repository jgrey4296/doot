#!/usr/bin/env python3
"""

"""
# ruff: noqa:

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import atexit#  for @atexit.register
import collections
import contextlib
import datetime
import enum
import faulthandler
import functools as ftz
import hashlib
import itertools as itz
import logging as logmod
import os
import pathlib as pl
import re
import sys
import time
import types
from bdb import BdbQuit
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
import jgdv.cli
import sh
import stackprinter
from jgdv import JGDVError, Mixin, Proto
from jgdv.cli.param_spec import LiteralParam, ParamSpec
from jgdv.cli.param_spec.builder_mixin import ParamSpecMaker_m
from jgdv.structs.chainguard import ChainGuard
from jgdv.util.plugins.selector import plugin_selector
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot._interface as API  # noqa: N812
import doot.errors
from doot.loaders.cmd import DootCommandLoader
from doot.loaders.plugin import DootPluginLoader
from doot.loaders.task import DootTaskLoader

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
from doot._abstract.loader import Loader_p
from doot._abstract import Command_p, Main_p

if TYPE_CHECKING:
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from jgdv import Maybe

    type Logger                            = logmod.Logger
    type DootError                         = doot.errors.DootError
    type DataSource                        = dict|ChainGuard
    type LoaderDict                        = dict[str, Loader_p]
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
env = os.environ
LOG_PREFIX : Final[str] = "----"

# Body:

class Loading_m:

    def _load(self) -> None:
        self._get_from_config()
        self._load_plugins()
        self._load_commands()
        self._load_tasks()
        self._load_cli_parser()

    def _get_from_config(self) -> None:
        """ Get main-relevant config settings """
        self.plugin_loader_key  : Final[str]               = doot.constants.entrypoints.DEFAULT_PLUGIN_LOADER_KEY
        self.command_loader_key : Final[str]               = doot.constants.entrypoints.DEFAULT_COMMAND_LOADER_KEY
        self.task_loader_key    : Final[str]               = doot.constants.entrypoints.DEFAULT_TASK_LOADER_KEY
        self.announce_voice     : Final[str]               = doot.constants.misc.ANNOUNCE_VOICE
        self.version_template   : Final[str]               = doot.constants.printer.doot.version_template
        self.HEADER_MSG         : Final[str]               = doot.constants.printer.doot_header
        self.preferred_cmd_loader                          = doot.config.on_fail("default").startup.loaders.command()
        self.preferred_task_loader                         = doot.config.on_fail("default").startup.loaders.task()
        self.preferred_parser                              = doot.config.on_fail("default").startup.loaders.parser()
        self.empty_call_cmd                                = doot.config.on_fail("list").startup.empty_cmd()
        self.implicit_task_cmd                             = doot.config.on_fail("run").startup.doot.implicit_task_cmd()


    def _load_plugins(self) -> None:
        """ Use the plugin loader to find all applicable `importlib.EntryPoint`s  """
        try:
            self.plugin_loader = DootPluginLoader()
            self.plugin_loader.setup()
            self.plugins : ChainGuard = self.plugin_loader.load()
            doot._load_aliases(data=self.plugins)
        except doot.errors.PluginError as err:
            self.shutdown_l.error("Plugins Not Loaded Due to Error: %s", err)
            raise

    def _load_commands(self) -> None:
        """ Select Commands from the discovered plugins,
        using the preferred cmd loader or the default
        """
        match plugin_selector(self.plugins.on_fail([], list).command_loader(),
                              target=self.preferred_cmd_loader,
                              fallback=DootCommandLoader):
            case type() as ctor:
                self.cmd_loader = ctor()
            case x:
                raise TypeError(type(x))

        match self.cmd_loader:
            case Loader_p():
                try:
                    self.cmd_loader.setup(self.plugins)
                    self.cmds = self.cmd_loader.load()
                except doot.errors.PluginError as err:
                    self.shutdown_l.error("Commands Not Loaded due to Error: %s", err)
                    self.cmds = ChainGuard()
            case x:
                raise TypeError("Unrecognized loader type", x)

    def _load_tasks(self) -> None:
        """ Load task entry points, using the preferred task loader,
        or the default
        """
        match plugin_selector(self.plugins.on_fail([], list).task_loader(),
                              target=self.preferred_task_loader,
                              fallback=DootTaskLoader):
            case type() as ctor:
                self.task_loader = ctor()
            case x:
                raise TypeError(type(x))

        match self.task_loader:
            case Loader_p():
                self.task_loader.setup(self.plugins)
                self.tasks = self.task_loader.load()
            case x:
                raise TypeError("Unrecognised loader type", x)

    def _load_cli_parser(self) -> None:
        match plugin_selector(self.plugins.on_fail([], list).parser(),
                              target=self.preferred_parser,
                              fallback=None):
            case None:
                parser_callbacks = None
            case type() as ctor:
                parser_callbacks = ctor()
            case x:
                raise TypeError(type(x))

        match parser_callbacks:
            case None:
                self.parser = jgdv.cli.ParseMachine()
            case jgdv.cli.ArgParser_p() as p:
                self.parser = jgdv.cli.ParseMachine(parser=p)
            case _:
                raise TypeError("Improper argparser specified", self.arg_parser)

class CLIArgParsing_m:

    def _parse_args(self) -> None:
        """ use the found task and command arguments to make sense of sys.argv """
        cmds_and_aliases = list(self.cmds.values())
        cmds_and_aliases += [(x, self.cmds[y[0]]) for x,y in doot.cmd_aliases.items()]
        subcmds = [("run",x) for x in self.tasks.values()]
        try:
            cli_args = self.parser(self.args[1:],
                                   head_specs=self.param_specs,
                                   cmds=cmds_and_aliases,
                                   # Associate tasks with the run cmd
                                   subcmds=subcmds)
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

        match cli_args:
            case dict() as d:
                doot.set_args(ChainGuard(d))
            case x:
                raise TypeError(type(x))

    def _handle_cli_args(self) -> Maybe[int]:
        """ Overlord specific cli arg responses. modify verbosity,
          print version, and _help.

          return True to end doot early
        """
        if doot.args.on_fail(False).head.args.verbose():
            self.overlord_l.user("Switching to Verbose Output")
            doot.log_config.set_level("NOTSET")

        if doot.args.on_fail(False).head.args.version():  # noqa: FBT4
            self.help_l.user(self.version_template, API.__version__)
            return API.ExitCodes.SUCCESS

        if doot.args.on_fail(False).head.args._help():  # noqa: FBT003
            self.help_l.user(self._help())
            return API.ExitCodes.SUCCESS

        if not self.args.on_fail(False).cmd.args.suppress_header():  # noqa: FBT003
            self.header_l.user(self.HEADER_MSG, extra={"colour": "green"})

        if self.args.on_fail(False).head.args.debug():  # noqa: FBT003
            self.overlord_l.user("Pausing for debugging")
            breakpoint()
            pass

        return None

    def _help(self) -> str:
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

class CmdRun_m:

    def _unalias_cmd(self, target:str) -> Maybe[str]:
        """ returns the unaliased command """
        match doot.cmd_aliases.on_fail(None)[target]():
            case None:
                # cmd name is not an alias
                return None
            case [name, *_] as args:
                # is an alias
                self.overlord_l.detail("Using Alias: %s", target)
                return name
            case x:
                raise TypeError(type(x))

    def _set_cmd_instance(self, cmd:Maybe[str]=None) -> None:
        """ Uses the full command name to get the instance of the command """
        match self.current_cmd:
            case None:
                pass
            case x:
                raise ValueError("Cmd shouldn't be already set")

        self.overlord_l.trace("Initial Retrieval attempt: %s", cmd)
        match self.cmds.get(cmd, None):
            case None if bool(doot.args.sub):
                self.overlord_l.detail("Falling Back to implicit: %s", self.implicit_task_cmd)
                self.current_cmd = self.cmds.get(self.implicit_task_cmd, None)
            case None if cmd.startswith("_") and cmd.endswith("_"):
                self.overlord_l.detail("Falling back to empty: %s", self.empty_call_cmd)
                self.current_cmd = self.cmds.get(self.empty_call_cmd, None)
            case Command_p():
                self.current_cmd = x
            case x:
                raise TypeError(type(x))

    def run_cmd(self, cmd:Maybe[str]=None) -> None:
        """
        The method run to trigger a doot workflow

        """
        match self._current_cmd:
            case Command_p() as cmd:
                pass
            case x:
                self.result_code = API.ExitCodes.BAD_CMD
                return
        try:
            # Do the cmd
            self.overlord_l.trace("---- Doot Calling Cmd: %s", cmd)
            cmd(self.tasks, self.plugins)
        except doot.errors.DootError as err:
            self._errored = err
            raise
        else:
            self.result_code = API.ExitCodes.SUCCESS
        finally:
            self.overlord_l.trace("---- Doot Cmd Call Complete")

class Shutdown_m:

    def shutdown(self) -> None:
        """ Doot has finished normally, so report on what was done """
        self.overlord_l.trace("Shutting Down Doot")
        match self.current_cmd:
            case None:
                pass
            case Command_p() as cmd:
                cmd.shutdown(self.tasks, self.plugins, errored=self._errored)

        self._record_defaulted_config_values()

        self.shutdown_l.user("")
        match self._errored:
            case doot.errors.DootError() as err:
                msg = doot.config.on_fail("Errored").shutdown.notify.fail_msg()
                self.shutdown_l.user("---- %s ----", msg)
                self.shutdown_l.error(err)
                self._announce_exit(msg)
            case Exception() as err:
                raise err
            case None:
                msg = doot.config.on_fail("").shutdown.notify.success_msg()
                self._announce_exit(msg)
                self.shutdown_l.user(msg)

        self.shutdown_l.user("---- Dooted ----")

    def _announce_exit(self, message:str) -> None:
        if not doot.config.on_fail(False).shutdown.notify.say_on_exit():  # noqa: FBT003
            return

        match sys.platform:
            case _ if "PRE_COMMIT" in env:
                return
            case "linux":
                sh.espeak(message)
            case "darwin":
                sh.say("-v", "Moira", "-r", "50", message)

    def _record_defaulted_config_values(self) -> None:
        if not doot.config.on_fail(False).shutdown.write_defaulted_values():  # noqa: FBT003
            return

        defaulted_file = doot.config.on_fail("{logs}/.doot_defaults.toml", pl.Path).shutdown.defaulted_values.path()
        expanded_path = doot.locs.Current[defaulted_file]
        if not expanded_path.parent.exists():
            self.shutdown_l.error("Couldn't log defaulted config values to: %s", expanded_path)
            return

        defaulted_toml = ChainGuard.report_defaulted()
        with pl.Path(expanded_path).open('w') as f:
            f.write("# default values used:\n")
            f.write("\n".join(defaulted_toml) + "\n\n")

class ExitHandlers_m:

    def _early_exit(self, err:Exception) -> int:  # noqa: ARG002
        self.shutdown_l.warning("Early Exit Triggered")
        return API.ExitCodes.EARLY

    def _missing_config_exit(self, err:Exception) -> int:  # noqa: ARG002
        base_target = pl.Path(doot.constants.on_fail(["doot.toml"]).paths.DEFAULT_LOAD_TARGETS()[0])
        # Handle missing files
        if base_target.exists():
            self.fail_l.exception("Base Config Target exists but it contains no valid config: %s", base_target)
        else:
            self.fail_l.warning("No toml config data found, create a doot.toml by calling `doot stub --config`")

        return API.ExitCodes.MISSING_CONFIG

    def _config_error_exit(self, err:Exception) -> int:
        self.fail_l.warning("Config Error: %s", " ".join(err.args))
        return API.ExitCodes.BAD_CONFIG

    def _task_failed_exit(self, err:Exception) -> int:
        self.fail_l.error("Task Error : %s : %s", err, exc_info=err)
        self.fail_l.error("Task Source: %s", err.task_source)
        return API.ExitCodes.TASK_FAIL

    def _bad_state_exit(self, err:Exception) -> int:
        self.fail_l.error("State Error: %s", " ".join(err.args))
        return API.ExitCodes.BAD_STATE

    def _bad_struct_exit(self, err:Exception) -> int:
        match err.args:
            case [str() as msg, dict() as errs]:
                self.fail_l.error("Struct Load Errors : %s", msg)
                self.fail_l.error("")
                for x,y in errs.items():
                    self.fail_l.error("---- File: %s", x)
                    for val in y:
                        self.fail_l.error("- %s", val)
                    else:
                        self.fail_l.error("")
            case _:
                self.fail_l.exception("Struct Load Error: %s", err, exc_info=err)

        return API.ExitCodes.BAD_STRUCT

    def _tracking_exit(self, err:Exception) -> int:
        self.fail_l.error("Tracking Failure: %s", " ".join(err.args))
        return API.ExitCodes.TRACKING_FAIL

    def _backend_exit(self, err:Exception) -> int:
        self.fail_l.exception("Backend Error: %s", " ".join(err.args), exc_info=err)
        return API.ExitCodes.BACKEND_FAIL

    def _frontend_exit(self, err:Exception) -> int:
        self.fail_l.error("%s", " ".join(err.args))
        return API.ExitCodes.FRONTEND_FAIL

    def _misc_doot_exit(self, err:Exception) -> int:
        self.fail_l.exception("%s", " ".join(err.args), exc_info=err)
        return API.ExitCodes.DOOT_FAIL

    def _not_implemented_exit(self, err:Exception) -> int:
        self.fail_l.exception("Not Implemented: %s", " ".join(err.args), exc_info=err)
        return API.ExitCodes.NOT_IMPLEMENTED

    def _python_exit(self, err:Exception) -> int:
        self.fail_l.exception("Python Error:", exc_info=err)
        self.fail_l.exception(f"Python Error, writing to {API.LASTERR}.", exc_info=None)
        pl.Path(API.LASTERR).write_text(stackprinter.format())
        return API.ExitCodes.PYTHON_FAIL

##--|

@Proto(Main_p)
@Mixin(Loading_m, CmdRun_m, ExitHandlers_m, Shutdown_m)
class DootMain:
    """ doot.main and the associated exit handlers

    Error's if doot hasn't got an overlord (aliased as the doot package)

    loads values from the overlord config,
    sets up runtime plugin system

    """

    plugins      : dict
    current_cmd  : Command_p
    plugins      : ChainGuard
    cmds         : ChainGuard
    tasks        : ChainGuard
    _errored     : DootError
    _current_cmd : str

    _help : ClassVar[tuple[str]] = tuple(["A Toml Specified Task Runner"])

    def __init__(self, *, cli_args:Maybe[list]=None) -> None:
        if not doot.is_setup:
            sys.exit(API.ExitCodes.NOT_SETUP)

        match cli_args:
            case None:
                self.args = sys.argv[:]
            case list() as vals:
                self.args = vals
            case x:
                raise TypeError(type(x))

        ##--|
        self.result_code : int                             = API.ExitCodes.INITIAL
        self.BIN_NAME                                      = self.args[-1].split('/')[-1]
        self.prog_name                                     = "doot"

        self.overlord_l      = doot.subprinter("overlord")
        self.header_l        = doot.subprinter("header")
        self.setup_l         = doot.subprinter("setup")
        self.help_l          = doot.subprinter("_help")
        self.shutdown_l      = doot.subprinter("shutdown")
        self.fail_l          = doot.subprinter("fail", prefix=API.fail_prefix)

    @property
    def param_specs(self) -> list[ParamSpec]:
        return [
            LiteralParam(name=self.prog_name),
            self.build_param(name="--version" , type=bool),
            self.build_param(name="--_help"    , type=bool),
            self.build_param(name="--verbose" , type=bool),
            self.build_param(name="--debug",    type=bool),
        ]

    def main(self) -> None:  # noqa: PLR0912
        """ The Main Doot CLI Program.
        Loads data and plugins before starting the requested command.
        """
        try:
            self._load()
            match self._handle_cli_args():
                case int() as x:
                    self.result_code = x
                    return
                case None:
                    pass

            target = doot.args.on_fail(self.implicit_task_cmd).cmd.name()
            match self._unalias_cmd(target):
                case str() as unaliased:
                    target = unaliased
                case None:
                    pass
            self._set_cmd_instance(target)
            self._run_cmd()
        except (doot.errors.EarlyExit, doot.errors.Interrupt, BdbQuit) as err:
            self.result_code = self._early_exit(err)
        except doot.errors.MissingConfigError as err:
            self.result_code = self._missing_config_exit(err)
        except doot.errors.ConfigError as err:
            self.result_code = self._config_error_exit(err)
        except (doot.errors.TaskFailed, doot.errors.TaskError) as err:
            self.result_code = self._task_failed_exit(err)
        except doot.errors.StateError as err:
            self.result_code = self._bad_state_exit(err)
        except doot.errors.StructLoadError as err:
            self.result_code = self._bad_struct_exit(err)
        except doot.errors.TrackingError as err:
            self.result_code = self._tracking_exit(err)
        except doot.errors.BackendError as err:
            self.result_code = self._backend_exit(err)
        except doot.errors.FrontendError as err:
            self.result_code = self._frontend_exit(err)
        except doot.errors.DootError as err:
            self.result_code = self._misc_doot_exit(err)
        except NotImplementedError as err:
            self.result_code = self._not_implemented_exit(err)
        except Exception as err:  # noqa: BLE001
            self.result_code = self._python_exit(err)
        finally:
            self.shutdown()
            sys.exit(self.result_code)
