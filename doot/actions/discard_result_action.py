##-- imports
from __future__ import annotations
##-- end imports

import sh
import doot
from doot.errors import DootTaskError
from doot._abstract import Action_p

class DootDiscardResultAction(Action_p):
    """
    An action that overrides failures,
    useful if something (*cough* godot *cough*)
    returns bad status codes
    """

    def __init__(self, *args, handler=None, **kwargs):
        self.handler = handler or self.default_handler

    def default_handler(self, result):
        logging.info("Task Failure Overriden: ", self.task.name)
        return None

    def __call__(self, *args, **kwargs):
        result = None

        try:
            cmd = getattr(sh, args[0])
            cmd(*args[1:])
        except sh.ErrorReturnCode as err:
            result = self.handler(result)

        return result
