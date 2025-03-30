#!/usr/bin/env python3
"""

"""
# mypy: disable-error-code="attr-defined"
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

# Body:

class Loading_m:
    """ mixin for triggering full loading  """

    def _load(self) -> None:
        doot.setup() # Loads the config
        self._set_constants()
        self._get_from_config()
        self._set_command_aliases()
        self._load_plugins()
        self._load_cli_parser()
        self._load_reporter()
        self._load_commands()
        self._load_tasks()

    def _set_constants(self) -> None:
        # Constants are always loaded, so need no on_fail
        self.plugin_loader_key  = doot.constants.entrypoints.DEFAULT_PLUGIN_LOADER_KEY
        self.command_loader_key = doot.constants.entrypoints.DEFAULT_COMMAND_LOADER_KEY
        self.task_loader_key    = doot.constants.entrypoints.DEFAULT_TASK_LOADER_KEY
        self.announce_voice     = doot.constants.misc.ANNOUNCE_VOICE
        self.version_template   = doot.constants.printer.version_template

    def _get_from_config(self) -> None:
        """ Get main-relevant config settings """
        # but config vals
        self.preferred_cmd_loader                          = doot.config.on_fail("default").startup.loaders.command()
        self.preferred_task_loader                         = doot.config.on_fail("default").startup.loaders.task()
        self.preferred_parser                              = doot.config.on_fail("default").startup.loaders.parser()
        self.empty_call_cmd                                = doot.config.on_fail("list").startup.empty_cmd()
        self.implicit_task_cmd                             = doot.config.on_fail("run").startup.doot.implicit_task_cmd()

    def _load_plugins(self) -> None:
        """ Use the plugin loader to find all applicable `importlib.EntryPoint`s  """
        from doot.loaders.plugin import DootPluginLoader
        try:
            self.plugin_loader = DootPluginLoader()
            self.plugin_loader.setup()
            self.plugins : ChainGuard = self.plugin_loader.load()
            doot._load_aliases(data=self.plugins)
        except doot.errors.PluginError as err:
            doot.report.error("Plugins Not Loaded Due to Error: %s", err)
            raise

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

    def _load_reporter(self) -> None:
        match plugin_selector(self.plugins.on_fail([], list).reporter(), fallback=False):
            case type() as ctor:
                doot.report = ctor()
            case False:
                pass
            case x:
                raise TypeError(type(x))


    def _load_commands(self) -> None:
        """ Select Commands from the discovered plugins,
        using the preferred cmd loader or the default
        """
        match plugin_selector(self.plugins.on_fail([], list).command_loader(),
                              target=self.preferred_cmd_loader):
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
                    doot.report.error("Commands Not Loaded due to Error: %s", err)
                    self.cmds = ChainGuard()
            case x:
                raise TypeError("Unrecognized loader type", x)

    def _load_tasks(self) -> None:
        """ Load task entry points, using the preferred task loader,
        or the default
        """
        match plugin_selector(self.plugins.on_fail([], list).task_loader(),
                              target=self.preferred_task_loader):
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

class CLIArgParsing_m:
    """ mixin for cli arg processing """

    def _parse_args(self) -> None:
        """ use the found task and command arguments to make sense of sys.argv """
        cmd_vals       = list(self.cmds.values())
        subcmds        = [("run",x) for x in self.tasks.values()]
        unaliased_args = self._unalias_raw_args(self.raw_args[1:])

        try:
            cli_args = self.parser(unaliased_args,
                                   head_specs=self.param_specs,
                                   cmds=cmd_vals,
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
            case dict() as parsed_args:
                doot.set_parsed_cli_args(ChainGuard(parsed_args))
            case x:
                raise TypeError(type(x))

    def _handle_cli_args(self) -> Maybe[int]:
        """ Overlord specific cli arg responses. modify verbosity,
          print version, and _help.

          return True to end doot early
        """
        if doot.args.on_fail(False).head.args.verbose():  # noqa: FBT003
            doot.report.user("Switching to Verbose Output")
            doot.log_config.set_level("NOTSET")

        if doot.args.on_fail(False).head.args.version():  # noqa: FBT003
            doot.report.user(self.version_template, API.__version__)
            return API.ExitCodes.SUCCESS

        if doot.args.on_fail(False).head.args.help():  # noqa: FBT003
            doot.report.user(self.help())
            return API.ExitCodes.SUCCESS

        if not doot.args.on_fail(False).cmd.args.suppress_header():  # noqa: FBT003
            doot.report.header()

        if doot.args.on_fail(False).head.args.debug():  # noqa: FBT003
            doot.report.user("Pausing for debugging")
            breakpoint()
            pass

        return None

    def help(self) -> str:
        help_lines = ["", f"Doot v{doot.__version__}", ""]
        help_lines += self._help_txt

        params = self.param_specs
        if bool(params):
            help_lines += ["", "Params:"]
            help_lines += sorted(str(x) for x in self.param_specs)

        help_lines.append("")
        help_lines.append("Commands: ")
        help_lines += sorted(x.helpline for x in self.cmds.values())

        return "\n".join(help_lines)

class CmdRun_m:
    """ mixin for actually running a command  """

    def _set_command_aliases(self) -> None:
        """ Read settings.commands.* and register aliases

        commands use doot.config.settings.commands.NAME,
        and within that, 'aliases' gives a dict of {alias=[args]}

        eg: commands.list.aliases.acts = ['--actions']
        ..  aliases 'doot acts'
        ..  to equiv of 'doot list --actions'

        """
        doot.report.trace("Setting Command Aliases")
        registered : dict = {}
        for name,details in doot.config.on_fail({}).settings.commands().items():
            for alias, args in details.on_fail({}, non_root=True).aliases().items():
                doot.report.trace("- %s -> %s", name, alias)
                registered[alias] = [name, *args]
        else:
            self.cmd_aliases = ChainGuard(registered)
            doot.report.trace("Finished Command Aliases")

    def _unalias_raw_args(self, raw:list[str]) -> list[str]:
        """ replaces aliases with their full command args """
        result        = []
        sep           = doot.constants.patterns.TASK_PARSE_SEP
        for i, x in enumerate(raw):
            match self.cmd_aliases.on_fail(None)[x]():
                case None:
                    # cmd name is not an alias
                    result.append(x)
                case list() if 0 < i and sep not in raw[i-1:i]:
                    result.append(x)
                case [name, *_] as args:
                    # is an alias
                    doot.report.trace("Using Alias: %s -> %s", x, name)
                    result += args
                case x:
                    raise TypeError(type(x))
        else:
            return result

    def _set_cmd_instance(self, cmd:Maybe[str]=None) -> None:
        """ Uses the full command name to get the instance of the command """
        match self.current_cmd, cmd:  # type: ignore[has-type]
            case None, str():
                cmd = cast(str, cmd)
            case None, None:
                raise ValueError("Cmd needs to exist")
            case x, _:
                raise ValueError("Cmd shouldn't be already set")

        assert(cmd is not None)
        logging.debug("Initial Retrieval attempt: %s", cmd)
        match self.cmds.get(cmd, None):
            case None if bool(doot.args.sub):
                doot.report.detail("Falling Back to implicit: %s", self.implicit_task_cmd)
                self.current_cmd = self.cmds.get(self.implicit_task_cmd, None)
            case None if cmd.startswith("_") and cmd.endswith("_"):
                doot.report.detail("Falling back to empty: %s", self.empty_call_cmd)
                self.current_cmd = self.cmds.get(self.empty_call_cmd, None)
            case Command_p() as x:
                self.current_cmd = x
            case x:
                raise TypeError(type(x), cmd)

    def run_cmd(self, _:Maybe[str]=None) -> None:
        """
        The method run to trigger a doot workflow

        """
        match self.current_cmd:
            case Command_p() as cmd:
                pass
            case x:
                self.result_code = API.ExitCodes.BAD_CMD
                return

        try:
            # Do the cmd
            logging.info("Doot Calling Cmd: %s", cmd)
            cmd(self.tasks, self.plugins)
        except doot.errors.DootError as err:
            self._errored = err
            raise
        else:
            self.result_code = API.ExitCodes.SUCCESS
        finally:
            logging.info("Doot Cmd Call Complete")

class Shutdown_m:
    """ mixin for cleaning up on and shutting down doot  """

    def shutdown(self) -> None:
        """ Doot has finished, report on what was done and how doot finished"""
        logging.info("Shutting Down Doot")
        match self.current_cmd:
            case None:
                pass
            case Command_p() as cmd:
                cmd.shutdown(self.tasks, self.plugins, errored=self._errored)

        doot.record_defaulted_config_values()

        doot.report.line()
        match self._errored:
            case doot.errors.DootError() as err:
                doot.report.set_state("fail", err=err, cb=self._announce_exit)
            case Exception() as err:
                raise err
            case None:
                doot.report.set_state("success", cb=self._announce_exit)

        doot.report.summary()

    def _announce_exit(self, message:str) -> None:
        """ triggers speech synthesis on exiting doot """
        if not doot.config.on_fail(False).shutdown.notify.say_on_exit():  # noqa: FBT003
            return

        match sys.platform:
            case _ if "PRE_COMMIT" in env:
                return
            case "linux":
                sh.espeak(message)
            case "darwin":
                sh.say("-v", "Moira", "-r", "50", message)

    def _install_at_exit(self):
        def goodbye(*args, **kwargs):
            doot.report.line("Dooted")

        atexit.register(goodbye)

class ExitHandlers_m:
    """ Mixin for handling different errors of doot """

    def _early_exit(self, err:Exception) -> int:  # noqa: ARG002
        doot.report.warn("Early Exit Triggered")
        return API.ExitCodes.EARLY

    def _missing_config_exit(self, err:Exception) -> int:  # noqa: ARG002
        base_target = pl.Path(doot.constants.on_fail(["doot.toml"]).paths.DEFAULT_LOAD_TARGETS()[0])
        # Handle missing files
        if base_target.exists():
            doot.report.error("Base Config Target exists but it contains no valid config: %s", base_target)
        else:
            doot.report.warn("No toml config data found, create a doot.toml by calling `doot stub --config`")

        return API.ExitCodes.MISSING_CONFIG

    def _config_error_exit(self, err:Exception) -> int:
        doot.report.warn("Config Error: %s", err)
        return API.ExitCodes.BAD_CONFIG

    def _task_failed_exit(self, err:Exception) -> int:
        logging.exception("Task Error : %s", err, exc_info=err)
        doot.report.error("Task Source: %s", err.task_source)
        return API.ExitCodes.TASK_FAIL

    def _bad_state_exit(self, err:Exception) -> int:
        doot.report.error("State Error: %s", err.args)
        return API.ExitCodes.BAD_STATE

    def _bad_struct_exit(self, err:Exception) -> int:
        match err.args:
            case [str() as msg, dict() as errs]:
                doot.report.error("Struct Load Errors : %s", msg)
                doot.report.error("")
                for x,y in errs.items():
                    doot.report.error("---- File: %s", x)
                    for val in y:
                        doot.report.error("- %s", val)
                    else:
                        doot.report.error("")
            case _:
                logging.exception("Struct Load Error: %s", err, exc_info=err)

        return API.ExitCodes.BAD_STRUCT

    def _tracking_exit(self, err:Exception) -> int:
        logging.exception("Tracking Failure: %s", err.args)
        return API.ExitCodes.TRACKING_FAIL

    def _backend_exit(self, err:Exception) -> int:
        logging.exception("Backend Error: %s", err.args, exc_info=err)
        return API.ExitCodes.BACKEND_FAIL

    def _frontend_exit(self, err:Exception) -> int:
        logging.exception("%s", err.args)
        return API.ExitCodes.FRONTEND_FAIL

    def _misc_doot_exit(self, err:Exception) -> int:
        logging.exception("%s", err.args, exc_info=err)
        return API.ExitCodes.DOOT_FAIL

    def _not_implemented_exit(self, err:Exception) -> int:
        logging.exception("Not Implemented: %s", err.args, exc_info=err)
        return API.ExitCodes.NOT_IMPLEMENTED

    def _python_exit(self, err:Exception) -> int:
        logging.exception("Python Error:", exc_info=err)
        pl.Path(API.LASTERR).write_text(stackprinter.format())
        doot.report.error(f"Python Error, full stacktrace written to {API.LASTERR}", exc_info=None)
        return API.ExitCodes.PYTHON_FAIL

##--|

@Proto(Main_p)
@Mixin(Loading_m, CLIArgParsing_m, CmdRun_m, ExitHandlers_m, Shutdown_m, ParamSpecMaker_m)
class DootMain:
    """ doot.main and the associated exit handlers

    Error's if doot hasn't got an overlord (aliased as the doot package)

    loads values from the overlord config,
    sets up runtime plugin system

    """

    current_cmd  : Maybe[Command_p]
    plugins      : ChainGuard
    cmds         : ChainGuard
    tasks        : ChainGuard
    _cmd_aliases : ChainGuard
    _errored     : Maybe[DootError]

    _help_txt    : ClassVar[tuple[str, ...]] = tuple(["A Toml Specified Task Runner"])

    def __init__(self, *, cli_args:Maybe[list]=None) -> None:
        match cli_args:
            case None:
                self.raw_args = sys.argv[:]
            case list() as vals:
                self.raw_args = vals
            case x:
                raise TypeError(type(x))

        ##--|
        self.result_code : int = API.ExitCodes.INITIAL
        self.BIN_NAME          = pl.Path(self.raw_args[0]).name
        self.prog_name         = "doot"
        self.current_cmd       = None
        self._errored          = None
        self.plugins           = ChainGuard()
        self.cmds              = ChainGuard()
        self.tasks             = ChainGuard()
        self._cmd_aliases      = ChainGuard()
        self.implicit_task_cmd = None

    @property
    def param_specs(self) -> list[ParamSpec]:
        """ The cli parameters of the main doot program. """
        return [
            LiteralParam(name=self.prog_name),
            self.build_param(name="--version" , type=bool),
            self.build_param(name="--help"    , type=bool),

            self.build_param(name="--verbose" , type=bool),
            self.build_param(name="--debug",    type=bool),
        ]

    def main(self) -> None:  # noqa: PLR0912
        """ The Main Doot CLI Program.
        Loads data and plugins before starting the requested command.

        Catches: doot errors, then NotImplementedError, then Exception

        has a 'finally' block to call sys.exit
        """
        try:
            self._load()
            self._parse_args()
            self._install_at_exit()
            match self._handle_cli_args():
                case None:
                    pass
                case int() as x:
                    self.result_code = x
                    return

            match doot.args.on_fail(self.implicit_task_cmd).cmd.name():
                case None:
                    raise doot.errors.CommandError("No available cmd")  # noqa: TRY301
                case str() as target:
                    self._set_cmd_instance(target)
                    self.run_cmd()
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
