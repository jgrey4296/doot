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
import re
from tomlguard import TomlGuard
##-- end std imports

# plugin names and loaders
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

# Loaded in doot.loaders.plugin_loader
# as pairs (name, import_path)
DEFAULT_PLUGINS                = {}

DEFAULT_PLUGINS['command']     = [("help"      ,      "doot.cmds.help_cmd:HelpCmd")           ,
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
                                  ("graph"     ,      "doot.cmds.graph_cmd:GraphCmd"),
                              ]

DEFAULT_PLUGINS['reporter']    = [("summary", "doot.reporters.summary_manager:DootReportManagerSummary"),
                                  ("stack",   "doot.reporters.stack_manager:DootReportManagerStack")
        ]

DEFAULT_PLUGINS['report-line'] = [("basic", "doot.reporters.basic_reporters:DootAlwaysReport"),
                                  ("time", "doot.reporters.basic_reporters:TimerReporter")
        ]

DEFAULT_PLUGINS['database']    = []
DEFAULT_PLUGINS['tracker']     = [("basic",      "doot.control.tracker:DootTracker")]
DEFAULT_PLUGINS['runner']      = [("basic",      "doot.control.runner:DootRunner"),
                                  ("step",       "doot.control.step_runner:DootStepRunner")
                                ]

DEFAULT_PLUGINS['parser']      = [("basic",      "doot.parsers.parser:DootArgParser")]
DEFAULT_PLUGINS['action']      = [("basic"  ,    "doot.actions.base_action:DootBaseAction"),

                                  ("shell" ,     "doot.actions.shell:DootShellAction"),
                                  ("interact",   "doot.actions.shell:DootInteractiveAction"),

                                  ("user",       "doot.actions.io:UserInput"),
                                  ("read"  ,     "doot.actions.io:ReadAction"),
                                  ("readJson",   "doot.actions.io:ReadJson"),
                                  ("copy"  ,     "doot.actions.io:CopyAction"),
                                  ("backup!",    "doot.actions.io:BackupAction"),
                                  ("write!" ,    "doot.actions.io:WriteAction"),
                                  ("dir!",       "doot.actions.io:EnsureDirectory"),
                                  ("delete!",    "doot.actions.io:DeleteAction"),
                                  ("break!",     "doot.actions.util:action_debugger"),
                                  ("type!",      "doot.actions.util:typecheck"),

                                  ("putPost",    "doot.actions.postbox:PutPostAction"),
                                  ("getPost",    "doot.actions.postbox:GetPostAction"),
                                  ("addState",   "doot.actions.state:AddStateAction"),
                                  ("addFn",      "doot.actions.state:AddStateFn"),

                                  ("sayTime",    "doot.actions.speak:SpeakTimeAction"),

                                  ("log",        "doot.actions.control_flow:LogAction"),
                                  ("pred?",      "doot.actions.control_flow:CancelOnPredicateAction"),
                                  ("installed?", "doot.actions.control_flow:AssertInstalled"),
                              ]

DEFAULT_PLUGINS['tasker']      = [("tasker"  , "doot.task.base_tasker:DootTasker"),
                                  ("walker" ,  "doot.task.dir_walker:DootDirWalker"),
                                  ("task"    , "doot.task.base_task:DootTask"),
                                  ("shadow"  , "doot.task.tree_shadower:DootTreeShadower"),
                                  ]
