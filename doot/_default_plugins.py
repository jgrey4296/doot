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
    'parser', 'action', "job"
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

DEFAULT_PLUGINS['parser']      = [("basic",   "doot.parsers.flexible:DootFlexibleParser")]
DEFAULT_PLUGINS['action']      = [("basic"  ,    "doot.actions.base_action:DootBaseAction"),

                                  ("shell" ,     "doot.actions.shell:DootShellAction"),
                                  ("interact",   "doot.actions.shell:DootInteractiveAction"),

                                  ("user",       "doot.actions.io:UserInput"),
                                  ("read"  ,     "doot.actions.io:ReadAction"),
                                  ("copy"  ,     "doot.actions.io:CopyAction"),
                                  ("move",       "doot.actions.io:MoveAction"),
                                  ("touch",      "doot.actions.io:TouchFileAction"),

                                  ("link!",      "doot.actions.io:LinkAction"),
                                  ("backup!",    "doot.actions.io:BackupAction"),
                                  ("write!" ,    "doot.actions.io:WriteAction"),
                                  ("dir!",       "doot.actions.io:EnsureDirectory"),
                                  ("delete!",    "doot.actions.io:DeleteAction"),

                                  ("json.read",  "doot.actions.json:ReadJson"),

                                  ("tar!",       "doot.actions.compression:TarCompressAction"),
                                  ("untar!",     "doot.actions.compression:TarDecompressAction"),
                                  ("tar.list",   "doot.actions.compression:TarListAction"),
                                  ("zip.new",    "doot.action.compression:ZipNewAction"),
                                  ("zip.add",    "doot.actions.compression:ZipAddAction"),
                                  ("zip.get",    "doot.actions.compression:ZipGetAction"),
                                  ("zip.list",  "doot.actions.compression:ZipListAction"),


                                  ("break!",     "doot.actions.util:action_debugger"),
                                  ("type!",      "doot.actions.util:typecheck"),

                                  ("putPost",    "doot.actions.postbox:PutPostAction"),
                                  ("getPost",    "doot.actions.postbox:GetPostAction"),
                                  ("addState",   "doot.actions.state:AddStateAction"),
                                  ("addFn",      "doot.actions.state:AddStateFn"),
                                  ("pathParts",  "doot.actions.state:PathParts"),

                                  ("sayTime",    "doot.actions.speak:SpeakTimeAction"),

                                  ("log",        "doot.actions.control_flow:LogAction"),
                                  ("skipIfFile", "doot.actions.control_flow:SkipIfFileExists"),
                                  ("pred?",      "doot.actions.control_flow:CancelOnPredicateAction"),
                                  ("installed?", "doot.actions.control_flow:AssertInstalled"),
                              ]

DEFAULT_PLUGINS['task']         = [("job"  ,     "doot.task.base_job:DootJob"),
                                   ("task" ,     "doot.task.base_task:DootTask"),
                                   ]

DEFAULT_PLUGINS['mixins']      = [("job:walker", "doot.mixins.job.walker:WalkerMixin"),
                                  ("job:shadow", "doot.mixins.job.shadower:WalkShadowerMixin"),
                                  ("job:sub",    "doot.mixins.job.subtask:SubMixin"),
                                  ("job:terse",  "doot.mixins.job.mini_builder:MiniBuilderMixin"),
                                  ("job:setup",  "doot.mixins.job.setup:SetupMixin"),
                                  ("job:headonly", "doot.mixins.job.mini_builder:HeadOnlyJobMixin"),
                                  ("job:limit", "doot.mixins.job.matcher:TaskLimitMixin"),
                                  ("job:match", "doot.mixins.job.matcher:PatternMatcherMixin"),
                                  ]
