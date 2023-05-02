"""

"""
from __future__ import annotations
import sys

import tomler
from doot.errors import CmdParseError, InvalidDooter, InvalidToml, InvalidCommand, InvalidTask
from doot.loaders.loader import get_loader
from doot.control import DootMain
from doot.overlord import DootOverlord_i
from doot.loaders.loader import DootTaskLoader, DootConfigLoader, DootCommandLoader

class DootOverlord(DootOverlord_i):
    # core doot commands
    # CMDS = (Help, Run, List, Clean, TabCompletion)

    def __init__(self, *, config_loader=None, config_filenames:tuple=('doot.toml', 'pyproject.toml'), extra_config:dict|Tomler=None, args:list=None):
        self.args        = args or sys.argv[:]
        self.BIN_NAME    = self.argss[0].split('/')[-1]

        config_loader      = config_loader or DootConfigLoader
        self.config_loader = config_loader.build(args, extra_config, config_filenames)
        self.config        = self.config_loader.load()
        self.cmd_loader    = self.config.loaders.command.build(self.config, self.CMDS)
        self.cmds          = self.cmd_loader.load()
        self.task_loader   = self.config.loaders.task.build(self.config)
        self.tasks         = self.task_loader.load()

    @staticmethod
    def print_version():
        """print doot version (includes path location)"""
        print(".".join([str(i) for i in VERSION]))
        print("lib @", os.path.dirname(os.path.abspath(__file__)))

    def __call__(self, args):
        """entry point for all commands

        :param all_args: list of string arguments from command line

        return codes:
          0: tasks executed successfully
          1: one or more tasks failed
          2: error while executing a task
          3: error before task execution starts,
             in this case the Reporter is not used.
             So be aware if you expect a different formatting (like JSON)
             from the Reporter.
        """
        pass
