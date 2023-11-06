##-- imports
from __future__ import annotations
import logging as logmod
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import sys
import sh
import doot
from doot.errors import DootTaskError
# from doot._abstract import Action_p
from doot.actions.base_action import DootBaseAction

class DootShellAction(DootBaseAction):
    """
    For actions in subshells.
    all other arguments are passed directly to the program, using `sh`

    The arguments of the action are held in spec


    TODO : handle shell output redirection, and error code ignoring (use action spec dict)
    """
    _toml_kwargs = ["background"]

    def __str__(self):
        return "Shell Action"

    def __call__(self, spec, task_state:dict) -> dict|bool|None:
        try:
            cmd      = getattr(sh, spec.args[0])
            expanded = [self.expand_str(x, task_state) for x in spec.args[1:]]
            result   = cmd(*expanded, _return_cmd=True, _bg=spec.kwargs.on_fail(False, bool).background())
            assert(result.exit_code == 0)
            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, spec.args[0], spec.args[1:])
            printer.info("%s", result, extra={"colour":"reset"})
            return True
        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], spec.args)
            return False
        except sh.ErrorReturnCode:
            printer.error("Shell Command '%s' exited with code: %s for args: %s", spec[0], result.exit_code, spec.args)
            return False

class DootInteractiveAction(DootBaseAction):
    """
      An interactive command, which uses the self.interact method as a callback for sh.
    """
    _toml_args = ["background"]
    aggregated = ""
    prompt     = ">>> "
    cont       = "... "

    def __call__(self, task_state:dict) -> dict|bool|None:
        try:
            cmd      = getattr(sh, spec.args[0])
            expanded = [self.expand_str(x, task_state) for x in spec.args[1:]]
            result   = cmd(*expanded, _return_cmd=True, _bg=spec.kwargs.on_fail(False, bool).background(), _out=self.interact, _out_bufsize=0, _tty_in=True, _unify_ttys=True)
            assert(result.exit_code == 0)
            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, spec.args[0], spec.args[1:])
            printer.info("%s", result, extra={"colour":"reset"})
            return True
        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], spec.args)
            return False
        except sh.ErrorReturnCode:
            printer.error("Shell Command '%s' exited with code: %s for args: %s", spec[0], result.exit_code, spec.args)
            return False


    def interact(self, char, stdin):
        # TODO possibly add a custom interupt handler
        self.aggregated += char
        if self.aggregated.endswith("\n"):
            printer.info(self.aggregated.strip())
            self.aggregated = ""

        if self.aggregated.startswith(self.prompt) :
            self.aggregated = ""
            stdin.put(input(self.prompt) + "\n")
        elif self.aggregated.startswith(self.cont):
            self.aggregated = ""
            val = input(self.cont)
            if bool(val):
                stdin.put("    " + input(self.cont) + "\n")
            else:
                stdin.put(input(self.cont) + "\n")
