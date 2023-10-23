##-- std imports
from __future__ import annotations

# import datetime
# import enum
import pathlib as pl
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from importlib import resources
##-- end std imports

##-- plugin names and loaders
PLUGIN_TOML_PREFIX         : Final = "doot.plugins" # (project.entry-points."doot.plugins")
FRONTEND_PLUGIN_TYPES      : Final = ['command', 'reporter', 'report-line']
BACKEND_PLUGIN_TYPES       : Final = [
    'database', 'tracker', 'runner',
    'command-loader', 'task-loader',
    'parser', 'action', "tasker"
    ]

DEFAULT_COMMAND_LOADER_KEY  : Final[str] =  "command-loader"

DEFAULT_TASK_LOADER_KEY     : Final[str] =  "task-loader"

DEFAULT_PLUGIN_LOADER_KEY   : Final[str] =  "plugin-loader"
##-- end plugin names and loaders

##-- default plugins
# Loaded in doot.loaders.plugin_loader
# as pairs (name, import_path)

DEFAULT_PLUGINS = {}

DEFAULT_PLUGINS['command']  = [("help"      ,      "doot.cmds.help_cmd:HelpCmd")           ,
                               ("run"       ,      "doot.cmds.run_cmd:RunCmd")             ,
                               ("list"      ,      "doot.cmds.list_cmd:ListCmd")           ,
                               ("clean"     ,      "doot.cmds.clean_cmd:CleanCmd")         ,
                               ("complete"  ,      "doot.cmds.complete_cmd:CompleteCmd")   ,
                               # ("serve"   ,      "doot.cmds.server_cmd:ServerCmd")       ,
                               ("daemon"    ,      "doot.cmds.daemon_cmd:DaemonCmd")       ,
                               ("stub"      ,      "doot.cmds.stub_cmd:StubCmd")           ,
                               ("step"      ,      "doot.cmds.step_cmd:StepCmd")           ,
                               ("plugins"   ,      "doot.cmds.plugins_cmd:PluginsCmd")     ,
                               ("locs"      ,      "doot.cmds.locs_cmd:LocsCmd")     ,
                              ]

DEFAULT_PLUGINS['reporter'] = [("summary", "doot.reporters.summary_manager:DootReportManagerSummary"),
                               ("stack",   "doot.reporters.stack_manager:DootReportManagerStack")
        ]
DEFAULT_PLUGINS['report-line'] = [("basic", "doot.reporters.basic_reporters:DootAlwaysReport"),
                                  ("time", "doot.reporters.basic_reporters:TimerReporter")
        ]
DEFAULT_PLUGINS['database'] = []

DEFAULT_PLUGINS['tracker']  = [("basic", "doot.control.tracker:DootTracker")]

DEFAULT_PLUGINS['runner']   = [("basic", "doot.control.runner:DootRunner")]

DEFAULT_PLUGINS['parser']   = [("basic", "doot.parsers.parser:DootArgParser")]

DEFAULT_PLUGINS['action']   = [("basic"  , "doot.actions.base_action:DootBaseAction"),
                               ("shell" , "doot.actions.shell_action:DootShellAction"),
                              ]

DEFAULT_PLUGINS['tasker']     = [("tasker"  , "doot.task.base_tasker:DootTasker"),
                                 ("globber" , "doot.task.globber:DootEagerGlobber"),
                                 ("task"    , "doot.task.base_task:DootTask"),
                                 ]

##-- end default plugins

##-- path and file names
TEMPLATE_PATH         : Final[pl.Path]       =  resources.files("doot.__templates")
TOML_TEMPLATE         : Final[pl.Path]       =  TEMPLATE_PATH / "basic_toml"
DOOTER_TEMPLATE       : Final[pl.Path]       =  TEMPLATE_PATH / "dooter"

DEFAULT_DOOTER        : Final[pl.Path]       =  pl.Path("dooter.py")

DEFAULT_LOAD_TARGETS  : Final[list[pl.Path]] =  [pl.Path(x) for x in ["doot.toml", "pyproject.toml", "Cargo.toml", "./.cargo/config.toml"]]

DEFAULT_STUB_TASK_NAME : Final[str] = "stub::stub"

##-- end path and file names

TASK_SEP            : FINAL[str]      = "::"
IMPORT_SEP          : FINAL[str]      = ":"
SUBTASKED_HEAD      : FINAL[str]      = "$head$"
CONFLICTED_ADD      : FINAL[str]      = "$conflict$"

DEFAULT_CLI_CMD     : Final[str]      = "run"

DEFAULT_TASK_PREFIX : Final[str]      = "task_"

DEFAULT_TASK_GROUP  : Final[str]      = "default"

ANNOUNCE_EXIT       : Final[bool]     = False

ANNOUNCE_VOICE      : Final[str]      = "Moira"

PRINTER_NAME        : Final[str]      = "doot._printer"
