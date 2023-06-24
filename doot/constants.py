##-- imports
from __future__ import annotations

# import abc
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
##-- end imports

PLUGIN_TOML_PREFIX         : Final = "doot.plugins" # (project.entry-points."doot.plugins")
FRONTEND_PLUGIN_TYPES      : Final = ['command', 'reporter']
BACKEND_PLUGIN_TYPES       : Final = ['database', 'tracker', 'runner', 'command_loader', 'task_loader', 'parser', 'action', 'task']

default_load_targets = [pl.Path(x) for x in ["doot.toml", "pyproject.toml", "Cargo.toml", "./.cargo/config.toml"]]
default_dooter       = pl.Path("dooter.py")

# Loaded in doot.loaders.plugin_loader
# as pairs (name, import_path)
default_plugins = {}

default_plugins['command']  = [("help",     "doot.cmds.help_cmd:HelpCmd"),
                               ("run",      "doot.cmds.run_cmd:RunCmd"),
                               ("list",     "doot.cmds.list_cmd:ListCmd"),
                               ("clean",    "doot.cmds.clean_cmd:CleanCmd"),
                               ("complete", "doot.cmds.complete_cmd:CompleteCmd"),
                               # ("serve",  "doot.cmds.server_cmd:ServerCmd"),
                               ("daemon",   "doot.cmds.daemon_cmd:DaemonCmd"),
                               ("stub",     "doot.cmds.stub_cmd:StubCmd"),
                               ("step",     "doot.cmds.step_cmd:StepCmd"),
                              ]

default_plugins['reporter'] = [("basic", "doot.reporters.basic:BasicReporter")]
default_plugins['database'] = []
default_plugins['tracker']  = [("basic", "doot.control.tracker:DootTracker")]
default_plugins['runner']   = [("basic", "doot.control.runner:DootRunner")]
default_plugins['parser']   = [("basic", "doot.parsers.parser:DootArgParser")]
default_plugins['action']   = [("cmd", "doot.actions.cmd_action:DootCmdAction"),
                                ("force", "doot.actions.force_cmd_action:ForceCmd"),
                                ("interactive", "doot.actions.interactive_cmd_action:InteractiveAction"),
                                ("py", "doot.actions.py_cmd_action:DootPyAction")
                                ]
default_plugins['task']     = [("basic", "doot.task.base_tasker:DootTasker"),
                               ("generaliser", "doot.task.generaliser:DootGeneraliser"),
                               ("glob", "doot.task.globber:DootEagerGlobber"),
                               ("dict", "doot.task.specialised_taskers:DictTasker"),
                               ("group", "doot.task.specialised_taskers:GroupTasker")]



default_cli_cmd            = "run"
default_task_prefix        = "task_"
default_task_group         = "default"

DEFAULT_COMMAND_LOADER_KEY = "command_loader"
DEFAULT_TASK_LOADER_KEY    = "task_loader"
DEFAULT_PLUGIN_LOADER_KEY  = "plugin_loader"
