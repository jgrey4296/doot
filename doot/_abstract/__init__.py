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

from .control import TaskTracker_i, TaskRunner_i
from .loader import CommandLoader_p, PluginLoader_p, TaskLoader_p
from .overlord import Overlord_p
from .cmd import Command_i
from .task import Action_p, TaskBase_i, Task_i, Job_i

from .dbm import DBManager_p
from .parser import ArgParser_i
from .reporter import Reporter_i, ReportLine_i
from .policy import FailPolicy_p
