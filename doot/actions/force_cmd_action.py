##-- imports
from __future__ import annotations
##-- end imports
from doot.actions.cmd_action import DootCmdAction

class ForceCmd(DootCmdAction):
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

        if isinstance(result, (TaskError, TaskFailed)):
            return self.handler(result)

        return result
