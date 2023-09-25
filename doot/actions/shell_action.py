##-- imports
from __future__ import annotations
import logging as logmod
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import sh
import doot
from doot.errors import DootTaskError
# from doot._abstract import Action_p
from doot.actions.base_action import DootBaseAction

class DootShellAction(DootBaseAction):
    """
    For actions in subshells.
    all other arguments are passed directly to the program, using `sh`

    The arguments of the action are held in self.spec
    __call__ is passed a *copy* of the task's state dictionary


    TODO : handle shell output redirection, and error code ignoring (use action spec dict)
    """

    def __str__(self):
        return f"Shell Action: {self.spec.args[0]}, Args: {self.spec.args[1:]}"

    def __call__(self, task_state_copy:dict) -> dict|bool|None:
        try:
            cmd    = getattr(sh, self.spec.args[0])
            expanded = [self.expand_str(x, task_state_copy) for x in self.spec.args[1:]]
            # TODO if args contains "{varname}", then replace with that varname from task_state_copy
            result = cmd(*expanded, _return_cmd=True, _bg=self.spec.on_fail(False, bool).background())
            assert(result.exit_code == 0)
            printer.info("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, self.spec.args[0], self.spec.args[1:])
            printer.info("%s", result, extra={"colour":"reset"})
            return True
        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], self.spec.args)
            return False
        except sh.ErrorReturnCode:
            printer.error("Shell Command '%s' exited with code: %s for args: %s", self.spec[0], result.exit_code, self.spec.args)
            return False
