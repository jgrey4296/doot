##-- imports
from __future__ import annotations
from doit.action import CmdAction
from doit.exceptions import InvalidTask, TaskFailed, TaskError
##-- end imports

human     = lambda x, y=False: tracemalloc._format_size(x, y)


def regain_focus(prog="iTerm"):
    """
    Applescript command to regain focus for if you lose it
    """
    return CmdAction(["osascript", "-e", f"tell application \"{prog}\"", "-e", "activate", "-e", "end tell"], shell=False)


class ForceCmd(CmdAction):
    """
    A CmdAction that overrides failures
    useful if something (*cough* godot *cough*)
    returns bad status codes
    """

    def __init__(self, *args, handler=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = handler or self.default_handler

    def default_handler(self, result):
        print("Task Failure Overriden: ", self.task.name)
        return None

    def execute(self, *args, **kwargs):
        result = super().execute(*args, **kwargs)

        if isinstance(result, (TaskError, TaskFailed)):
            return self.handler(result)

        return result
