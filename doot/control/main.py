#!/usr/bin/env python3
"""

"""
# : disable-error-code="attr-defined"
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
from jgdv.cli._interface import EMPTY_CMD
from jgdv.cli.param_spec import ParamSpec, LiteralParam
from jgdv.cli import ParamSpecMaker_m
from jgdv.logging import JGDVLogConfig
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.chainguard._interface import ChainProxy_p
from jgdv.util.plugins.selector import plugin_selector
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot._interface as API  # noqa: N812
from doot.cmds._interface import AcceptsSubcmds_p
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
from typing import no_type_check, final, overload

if TYPE_CHECKING:
    from .loaders._interface  import Loader_p
    from ._interface import Main_p
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from logmod import Logger
    from jgdv import Maybe
    from jgdv.cli import ParamSource_p, ParseMachine
    from doot.errors import DootError

    type DataSource                        = dict|ChainGuard
    type LoaderDict                        = dict[str, Loader_p]

##--|
from doot.cmds._interface import Command_p
from ._interface import Main_i
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
env                                       = os.environ
DEFAULT_EMPTY_CMD     : Final[list[str]]  = ["--help"]
DEFAULT_IMPLICIT_CMD  : Final[list[str]]  = ["run"]
PROG_NAME             : Final[str]        = "doot"

##--| controllers

class LoadingController:
    """ mixin for triggering full loading  """
    type DM = Main_p

    _version_template   : str

    def load(self, obj:DM) -> None:
        # Load and initialise the config:
        doot.setup() # type: ignore[attr-defined]
        # Then use it for everything else:
        doot.load()
        self.update_command_aliases(obj)

    def update_command_aliases(self, obj:DM) -> None:
        """ Read settings.commands.* and register aliases

        commands use doot.config.settings.commands.NAME,
        and within that, 'aliases' gives a dict of {alias=[args]}

        eg: commands.list.aliases.acts = ['--actions']
        ..  aliases 'doot acts'
        ..  to equiv of 'doot list --actions'

        """
        name        : str
        details     : dict
        registered  : dict
        doot.report.trace("Setting Command Aliases")
        registered = {}
        for name,details in doot.config.on_fail({}).settings.commands().items():
            for alias, args in ChainGuard(details).on_fail({}, non_root=True).aliases().items():
                doot.report.trace("- %s -> %s", name, alias)
                registered[alias] = [name, *args]
        else:
            doot.cmd_aliases = ChainGuard(registered)
            doot.report.trace("Finished Command Aliases")

class CLIController:
    """ mixin for cli arg processing """
    type DM = DootMain

    def parse_args(self, obj:DM, *, override:Maybe[list]=None) -> None:
        """ use loaded cmd and tasks to parse sys.argv """
        cmds            : list
        subcmds         : list
        unaliased_args  : list[str]
        implicits       : dict[str,list[str]]
        parser          : ParseMachine
        ##--|

        parser          = self._load_cli_parser(obj,
                                                target=doot.config.on_fail("default").startup.loaders.parser())
        cmds            = list(doot.loaded_cmds.values())
        subcmds         = self._map_subcmd_constraints()
        unaliased_args  = self._unalias_raw_args(obj)
        implicits       = self._construct_implicits()

        try:
            cli_args  = parser(unaliased_args,
                               prog=cast("ParamSource_p", obj),
                               cmds=cmds,
                               subs=subcmds,
                               implicits=implicits,
                               )
        except jgdv.cli.errors.HeadParseError as err:
            raise doot.errors.FrontendError("Doot Head Failed to Parse", err) from None
        except jgdv.cli.errors.CmdParseError as err:
            raise doot.errors.FrontendError("Unrecognised Command Called", err) from None
        except jgdv.cli.errors.SubCmdParseError as err:
            raise doot.errors.FrontendError("Unrecognised Task Called", err.args[1]) from None
        except jgdv.cli.errors.ArgParseError as err:
            raise doot.errors.FrontendError("Parsing arguments for command/task failed", err) from None
        except jgdv.cli.ParseError as err:
            raise doot.errors.ParseError("Failed to Parse provided cli args", err) from None
        else:
            match cli_args:
                case dict() as parsed_args:
                    doot.set_parsed_cli_args(parsed_args, override=bool(override)) # type: ignore[attr-defined]
                case x:
                    raise TypeError(type(x))

    def _load_cli_parser(self, obj:DM, *, target:str="default") -> ParseMachine:
        match plugin_selector(doot.loaded_plugins.on_fail([], list).parser(),
                              target=target,
                              fallback=None):
            case None:
                parser_model = None
            case type() as ctor:
                parser_model = ctor()
            case  x:
                raise TypeError(type(x))

        match parser_model:
            case None:
                from .arg_parser_model import DootArgParserModel  # noqa: PLC0415
                return jgdv.cli.ParseMachine(DootArgParserModel())
            case jgdv.cli.ArgParserModel_p() as p:
                return jgdv.cli.ParseMachine(parser=p)
            case _:
                raise TypeError("Improper parser model specified", parser_model)

    def _unalias_raw_args(self, obj:DM) -> list[str]:
        """ replaces aliases with their full command args.

        Just a simple, literal, find and replace
        """
        raw     = obj.raw_args
        result  = []
        sep     = doot.constants.patterns.TASK_PARSE_SEP
        for i, x in enumerate(raw):
            match doot.cmd_aliases.on_fail(None)[x]():
                case None:
                    # cmd name is not an alias
                    result.append(x)
                case list() if 0 < i and sep not in raw[i-1:i]:
                    result.append(x)
                case [name, *_] as args:
                    # is an alias
                    doot.report.trace("Using Alias: %s -> %s", x, args)
                    result += args
                case x:
                    raise TypeError(type(x))
        else:
            return result

    def _construct_implicits(self) -> dict[str, list[str]]:
        result : dict = {}
        match doot.config.on_fail(DEFAULT_IMPLICIT_CMD, list).startup.implicit_task_cmd():
            case [x, *_] as xs:
                result[x] = xs
            case x:
                raise TypeError(type(x))

        return result

    def _map_subcmd_constraints(self) -> list[tuple[tuple[str, ...], ParamSource_p]]:
        subcmd_handlers  = tuple(x for x,y in doot.loaded_cmds.items() if isinstance(y, AcceptsSubcmds_p))
        subcmds          = [(subcmd_handlers, x) for x in doot.loaded_tasks.values()]
        return subcmds

class CmdController:
    """ mixin for actually running a command  """
    type DM = DootMain

    def prepare(self, obj:DM) -> None:
        pass

    def run_cmds(self, obj:DM) -> None:
        try:
            for name, calls in doot.args.cmds:
                cmd = self.get_cmd_instance(obj, cmd=name)
                for idx in range(len(calls)):
                    obj.result_code = self.run_cmd(idx=idx, cmd=cmd)
                else:
                    pass
            else:
                pass

        except doot.errors.DootError as err:
            obj._errored = err
            raise
        else:
            pass

    def get_cmd_instance(self, obj:DM, *, cmd:str) -> Command_p:
        """ Uses the full command name to get the instance of the command """
        x : Any
        ##--|
        logging.debug("Initial Retrieval attempt: %s", cmd)
        match doot.loaded_cmds.get(cmd, None):
            case Command_p() as x:
                return x
            case x:
                raise TypeError(type(x), cmd)

    def run_cmd(self, *, idx:int, cmd:Command_p) -> int:
        """
        The method run to trigger a doot workflow

        """
        match cmd:
            case Command_p() as cmd:
                pass
            case x:
                return API.ExitCodes.BAD_CMD

        # Do the cmd
        logging.info("Doot Calling Cmd: %s", cmd.name)
        cmd(idx, doot.loaded_tasks, doot.loaded_plugins)
        return API.ExitCodes.SUCCESS

class ShutdownController:
    """ mixin for cleaning up on and shutting down doot  """
    type DM = DootMain

    def prepare(self, obj:DM) -> None:
        self.install_handler(obj)

    def shutdown(self, obj:DM) -> None:
        """ Doot has finished, report on what was done and how doot finished"""
        logging.info("Shutting Down Doot")
        match obj.current_cmd:
            case None:
                pass
            case Command_p() as cmd:
                cmd.shutdown(doot.loaded_tasks, doot.loaded_plugins, errored=obj._errored)

        self.record_defaulted_config_values()

        doot.report.line()
        match obj._errored:
            case doot.errors.DootError() as err:
                doot.report.log.exception("fail")
            case Exception() as err:
                raise err
            case None:
                pass

        doot.report.summary()

    def install_handler(self, obj:DM) -> None:
        """ Install an exit handler """
        report_val : str
        match doot.config.on_fail(None).shutdown.notify.exit():
            case None: # No config value, use default
                report_val = "Dooted"
            case False:
                return
            case str() as x:
                report_val = x

        def goodbye(*args, **kwargs) -> None: # noqa: ARG001, ANN002, ANN003
            doot.report.line(report_val)

        atexit.register(goodbye)

    def announce_exit(self, message:str) -> None:
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

    def record_defaulted_config_values(self) -> None:
        if not doot.config.on_fail(False).shutdown.write_defaulted_values():  # noqa: FBT003
            return

        defaulted_file : str     = doot.config.on_fail("{logs}/.doot_defaults.toml", str).shutdown.defaulted_values.path()
        expanded_path  : pl.Path = doot.locs[defaulted_file]
        if not expanded_path.parent.exists():
            doot.report.error("Couldn't log defaulted config values to: %s", expanded_path)
            return

        defaulted_toml = ChainGuard.report_defaulted()
        with pl.Path(expanded_path).open('w') as f:
            f.write("# default values used:\n")
            f.write("\n".join(defaulted_toml) + "\n\n")

class ExitController:
    """ Mixin for handling different errors of doot """
    type DM = DootMain

    def _early_exit(self, err:Exception) -> int:  # noqa: ARG002
        doot.report.warn("Early Exit Triggered")
        return API.ExitCodes.EARLY

    def _missing_config_exit(self, err:Exception) -> int:
        load_targets: list = doot.constants.on_fail(["doot.toml"]).paths.DEFAULT_LOAD_TARGETS()
        base_target = pl.Path(load_targets[0])
        # Handle missing files
        if base_target.exists():
            doot.report.error("[%s] : Base Config Target exists but it contains no valid config: %s",
                              type(err).__name__, base_target)
        else:
            doot.report.warn("[%s] : No toml config data found, create a doot.toml by calling `doot stub --config`",
                             type(err).__name__)

        return API.ExitCodes.MISSING_CONFIG

    def _config_error_exit(self, err:Exception) -> int:
        doot.report.warn("[%s] : Config Error: %s", type(err).__name__, err)
        return API.ExitCodes.BAD_CONFIG

    def _task_failed_exit(self, err:Exception) -> int:
        doot.report.error("[%s] : Task Error : %s", type(err).__name__, err, exc_info=err)
        doot.report.error("[%s] : Task Source: %s", type(err).__name__, err.task_source)
        return API.ExitCodes.TASK_FAIL

    def _bad_state_exit(self, err:Exception) -> int:
        doot.report.error("[%s] : State Error: %s", type(err).__name__, err.args)
        return API.ExitCodes.BAD_STATE

    def _bad_struct_exit(self, err:Exception) -> int:
        match err.args:
            case [str() as msg, dict() as errs]:
                doot.report.error("[%s] : Struct Load Errors : %s", type(err).__name__, msg)
                doot.report.error("")
                for x,y in errs.items():
                    doot.report.error("---- File: %s", x)
                    for val in y:
                        doot.report.error("- %s", val)
                    else:
                        doot.report.error("")
            case _:
                doot.report.error("[%s] : Struct Load Error: %s", type(err).__name__, err, exc_info=err)

        return API.ExitCodes.BAD_STRUCT

    def _tracking_exit(self, err:Exception) -> int:
        doot.report.error("[%s] : Tracking Failure: %s", type(err).__name__, err.args)
        return API.ExitCodes.TRACKING_FAIL

    def _backend_exit(self, err:Exception) -> int:
        doot.report.error("[%s] : Backend Error: %s", type(err).__name__, err.args, exc_info=err)
        return API.ExitCodes.BACKEND_FAIL

    def _frontend_exit(self, err:Exception) -> int:
        doot.report.error("[%s] : %s", type(err).__name__, " : ".join(err.args))
        return API.ExitCodes.FRONTEND_FAIL

    def _misc_doot_exit(self, err:Exception) -> int:
        doot.report.error("[%s] : %s", type(err).__name__, err.args, exc_info=err)
        return API.ExitCodes.DOOT_FAIL

    def _not_implemented_exit(self, err:Exception) -> int:
        doot.report.error("[%s] : Not Implemented: %s", type(err).__name__, err.args, exc_info=err)
        return API.ExitCodes.NOT_IMPLEMENTED

    def _python_exit(self, err:Exception) -> int:
        doot.report.error("[%s] : Python Error:", type(err).__name__, exc_info=err)
        lasterr : pl.Path = pl.Path(API.LASTERR).resolve()
        lasterr.write_text(stackprinter.format())
        doot.report.error(f"[{type(err).__name__}] : Python Error, full stacktrace written to {lasterr}", exc_info=None)
        return API.ExitCodes.PYTHON_FAIL


##--|

@Proto(Main_i)
class DootMain(ParamSpecMaker_m):
    """ doot.main and the associated exit handlers

    Error's if doot hasn't got an overlord (aliased as the doot package)

    loads values from the overlord config,
    sets up runtime plugin system

    """
    _loading     : ClassVar[LoadingController]   = LoadingController()
    _cli         : ClassVar[CLIController]       = CLIController()
    _cmd         : ClassVar[CmdController]       = CmdController()
    _shutdown    : ClassVar[ShutdownController]  = ShutdownController()
    _exit        : ClassVar[ExitController]      = ExitController()

    ##--|
    result_code  : int
    bin_name     : str
    prog_name    : str
    current_cmd  : Maybe[Command_p]
    _errored     : Maybe[Exception]
    _help_txt  = tuple(["A Toml Specified Task Runner"])

    def __init__(self, *, cli_args:Maybe[list]=None) -> None:
        match cli_args:
            case None:
                self.raw_args = sys.argv[:]
            case list() as vals:
                self.raw_args = vals
            case x:
                raise TypeError(type(x))

        ##--|
        self.result_code         = API.ExitCodes.INITIAL
        self.bin_name            = pl.Path(self.raw_args[0]).name
        self.prog_name           = "doot"
        self.current_cmd         = None
        self.parser              = None
        self._errored            = None
        self.log_config          = JGDVLogConfig()

    @property
    def name(self) -> str:
        return PROG_NAME

    def param_specs(self) -> list[ParamSpec]:
        """ The cli parameters of the main doot program. """
        return [
            # TODO may need to control the sort of this literal
            LiteralParam(name=self.prog_name, desc="The Program Name"),
            self.build_param(name="--version" , type=bool, desc="Print the version number"),
            self.build_param(name="--help"    , type=bool, desc="Print this help"),

            self.build_param(name="--verbose" , type=bool, desc="Increase Verbosity"),
            self.build_param(name="--debug",    type=bool, desc="Activate breakpoints"),
        ]

    def help(self) -> str:
        help_lines = ["", f"Doot v{doot.__version__}", ""]
        help_lines += self._help_txt

        params = self.param_specs()
        if bool(params):
            help_lines += ["", "Params:"]
            help_lines += (x.help_str() for x in self.param_specs())

        help_lines.append("")
        help_lines.append("Commands: ")
        help_lines += sorted(x.helpline for x in doot.loaded_cmds.values())

        return "\n".join(help_lines)

    def setup_logging(self) -> None:
        self.log_config.setup(doot.config)

    def handle_cli_args(self) -> Maybe[int]:
        """ Overlord specific cli arg responses.
        Modifies:
        - verbosity,
        - print version
        - header suppression
        - help printing
        - debugger entry

          return an int to give an override result code
        """
        _version_template : str
        ##--|
        _version_template = doot.constants.printer.version_template
        # type: ignore[attr-defined]
        if doot.args.on_fail(False).prog.args.verbose():  # noqa: FBT003
            doot.report.user("Switching to Verbose Output")
            doot.log_config.set_level("DEBUG")

        if doot.args.on_fail(False).prog.args.version(): # noqa: FBT003
            doot.report.user(_version_template, API.__version__)
            return API.ExitCodes.SUCCESS

        if not doot.args.on_fail(False).prog.args.suppress_header(): # noqa: FBT003
             doot.report.header()

        if not bool(doot.args.on_fail({}).cmds()) and doot.args.on_fail(False).help(): # noqa: FBT003
            helptxt = self.help()
            doot.report.user(helptxt)
            return API.ExitCodes.SUCCESS

        if doot.args.on_fail(False).prog.args.debug(): # noqa: FBT003
            doot.report.user("Pausing for debugging")
            breakpoint()
            pass

        return None

    def __call__(self) -> None:  # noqa: PLR0912
        """ The Main Doot CLI Program.
        Loads data and plugins before starting the requested command.

        Catches: doot errors, then NotImplementedError, then Exception

        has a 'finally' block to call sys.exit
        """
        x : Any
        try:
            self._loading.load(self)

            self._cli.parse_args(self)
            match self.handle_cli_args():
                case None:
                    pass
                case int() as x:
                    self.result_code = x
                    return

            self._exit.prepare(self)
            self._cmd.run_cmds(self)
        except (doot.errors.EarlyExit, doot.errors.Interrupt, BdbQuit) as err:
            self.result_code = self._early_exit(err)
        except doot.errors.MissingConfigError as err:
            match self.raw_args:
                case [*_, "stub", "--config"]:
                    from doot.cmds.stub_cmd import StubCmd  # noqa: PLC0415
                    stubber = StubCmd()
                    stubber._stub_doot_toml()
                case _:
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
            self._shutdown.shutdown(self)
            sys.exit(self.result_code)
