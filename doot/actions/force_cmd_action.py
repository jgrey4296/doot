##-- imports
from __future__ import annotations
##-- end imports

import doot
from doot.errors import DootTaskError
from doot._abstract.action import Action_p

class ForceCmd(Action_p):
    """
    A CmdAction that overrides failures
    useful if something (*cough* godot *cough*)
    returns bad status codes
    """

    def __init__(self, *args, handler=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = handler or self.default_handler

    def default_handler(self, result):
        logging.info("Task Failure Overriden: ", self.task.name)
        return None

    def execute(self, *args, **kwargs):
        result = super().execute(*args, **kwargs)

        if isinstance(result, DootTaskError):
            return self.handler(result)

        return result
