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

default_cmds = ["doot.cmds.help_cmd:HelpCmd",
                "doot.cmds.run_cmd:RunCmd",
                "doot.cmds.list_cmd:ListCmd",
                "doot.cmds.clean_cmd:CleanCmd",
                "doot.cmds.complete_cmd:CompleteCmd",
                "doot.cmds.server_cmd:ServerCmd",
                "doot.cmds.daemon_cmd:DaemonCmd"
    ]

default_cli_cmd     = "run"
default_task_prefix = "task_"
default_task_group  = "default"
