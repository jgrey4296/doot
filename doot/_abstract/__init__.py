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

from .control import TaskOrdering_p, TaskStatus_i, TaskTracker_i, TaskRunner_i
from .loader import CommandLoader_p, PluginLoader_p, TaskLoader_p
from .action import Action_p
from .cmd import Command_i
from .dbm import DBManager_p

from .overlord import Overlord_p
from .parser import ArgParser_i
from .reporter import Reporter_i

from .task import Task_i
from .tasker import Tasker_i
