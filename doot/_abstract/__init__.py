"""
Interfaces and Protocols for using Doot.

Definitions:

Protocols  - Functional specifications an object needs to implement to be used
Data       - Structural specifications an object need to possess
Interfaces - Combined Functional and Structural specifications

Protocols have names: {}_p
Data have names:      {}_d
Interfaces have names {}_i

Interfaces need to be inherited from, and their __init__ method called.
"""

from importlib.metadata import EntryPoint
from .control import TaskTracker_p, TaskRunner_p
from .loader import Loader_p
from .overlord import Overlord_p, Main_p
from .cmd import Command_p, Command_d
from .task import Action_p, Task_d, Job_p, Task_p
from .protocols import SpecStruct_p

type Loaders_p             = CommandLoader_p | PluginLoader_p | TaskLoader_p
type PluginLoader_p        = Loader_p[EntryPoint]
type CommandLoader_p       = Loader_p[Command_p]
type TaskLoader_p          = Loader_p[SpecStruct_p]
