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
FRONTEND_PLUGIN_TYPES      : Final = ['command', 'reporter']
BACKEND_PLUGIN_TYPES       : Final = [
    'database', 'tracker', 'runner',
    'command_loader', 'task_loader',
    'parser', 'action', "tasker"
    ]

DEFAULT_COMMAND_LOADER_KEY  : Final[str] =  "command_loader"

DEFAULT_TASK_LOADER_KEY     : Final[str] =  "task_loader"

DEFAULT_PLUGIN_LOADER_KEY   : Final[str] =  "plugin_loader"
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
                              ]

DEFAULT_PLUGINS['reporter'] = [("basic", "doot.reporters.basic:BasicReporter")]

DEFAULT_PLUGINS['database'] = []

DEFAULT_PLUGINS['tracker']  = [("basic", "doot.control.tracker:DootTracker")]

DEFAULT_PLUGINS['runner']   = [("basic", "doot.control.runner:DootRunner")]

DEFAULT_PLUGINS['parser']   = [("basic", "doot.parsers.parser:DootArgParser")]

DEFAULT_PLUGINS['action']   = [("shell"       , "doot.actions.shell_action:DootShellAction")                          ,
                               ("discard"     , "doot.actions.discard_result_action:DootDiscardResultAction")         ,
                               ("interactive" , "doot.actions.interactive_shell_action:DootInteractiveShellAction")   ,
                               ("py"          , "doot.actions.py_action:DootPyAction")                                ,
                               ]

DEFAULT_PLUGINS['tasker']     = [("basic"          , "doot.task.base_tasker:DootTasker")             ,
                                 ("generaliser"    , "doot.task.generaliser:DootGeneraliser")        ,
                                 ("glob"           , "doot.task.globber:DootEagerGlobber")           ,
                                 ("dict"           , "doot.task.specialised_taskers:DictTasker")     ,
                                 ("group"          , "doot.task.specialised_taskers:GroupTasker")    ,
                                 ]

##-- end default plugins

##-- path and file names
TEMPLATE_PATH         : Final[pl.Path]       =  resources.files("doot.__templates")
TOML_TEMPLATE         : Final[pl.Path]       =  TEMPLATE_PATH / "basic_toml"
DOOTER_TEMPLATE       : Final[pl.Path]       =  TEMPLATE_PATH / "dooter"

DEFAULT_DOOTER        : Final[pl.Path]       =  pl.Path("dooter.py")

DEFAULT_LOAD_TARGETS  : Final[list[pl.Path]] =  [pl.Path(x) for x in ["doot.toml", "pyproject.toml", "Cargo.toml", "./.cargo/config.toml"]]

##-- end path and file names

DEFAULT_CLI_CMD     : Final[str]  = "run"

DEFAULT_TASK_PREFIX : Final[str]  = "task_"

DEFAULT_TASK_GROUP  : Final[str]  = "default"

ANNOUNCE_EXIT       : Final[bool] = False

ANNOUNCE_VOICE      : Final[str]  = "Moira"

PRINTER_NAME        : Final[str]  = "doot._printer"
