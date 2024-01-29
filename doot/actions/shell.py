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
from doot._abstract import Action_p
from doot.actions.base_action import DootBaseAction
from doot.structs import DootKey

BACKGROUND = DootKey.make("background")
UPDATE     = DootKey.make("update_")
NOTTY      = DootKey.make("notty")
ENV        = DootKey.make("shenv_")

@doot.check_protocol
class DootShellAction(Action_p):
    """
    For actions in subshells.
    all other arguments are passed directly to the program, using `sh`


    can use a pre-baked sh passed into what "shenv_" points to
    """
    _toml_kwargs = [BACKGROUND, NOTTY, ENV]

    def __call__(self, spec, state:dict) -> dict|bool|None:
        result     = None
        update     = UPDATE.redirect(spec) if UPDATE in spec.kwargs else None
        background = bool(BACKGROUND.to_type(spec, state))
        notty      = not bool(NOTTY.to_type(spec, state))
        env        = ENV.to_type(spec, state, on_fail=sh)
        try:
            cmd                     = getattr(env, DootKey.make(spec.args[0], explicit=True).expand(spec, state))
            keys                    = [DootKey.make(x, explicit=True) for x in spec.args[1:]]
            expanded                = [x.expand(spec, state) for x in keys]
            result                  = cmd(*expanded, _return_cmd=True, _bg=background, _tty_out=notty)
            assert(result.exit_code == 0)

            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, spec.args[0], spec.args[1:])
            if not update:
                printer.info("%s", result, extra={"colour":"reset"})
                return True

            return { update : result.stdout }

        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], spec.args)
            return False
        except sh.ErrorReturnCode as err:
            printer.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                printer.error("%s", err.stdout.decode())

            printer.info("")
            if bool(err.stderr):
                printer.error("%s", err.stderr.decode())

            return False

@doot.check_protocol
class DootInteractiveAction(Action_p):
    """
      An interactive command, which uses the self.interact method as a callback for sh.
    """
    _toml_args = ["background"]
    aggregated = ""
    prompt     = ">>> "
    cont       = "... "

    def __call__(self, spec, state:dict) -> dict|bool|None:
        try:
            self.prompt = spec.kwargs.on_fail(DootInteractiveAction.prompt, str).prompt()
            self.cont   = spec.kwargs.on_fail(DootInteractiveAction.cont, str).cont()

            cmd      = getattr(sh, spec.args[0])
            args     = spec.args[1:]
            keys     = [DootKey.make(x, explicit=True) for x in args]
            expanded = [x.expand(spec, state) for x in keys]
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
        self.aggregated += str(char)
        if self.aggregated.endswith("\n"):
            printer.info(self.aggregated.strip())
            self.aggregated = ""

        if self.aggregated.startswith(self.prompt) :
            prompt = self.aggregated[:] + ": "
            self.aggregated = ""
            stdin.put(input(prompt) + "\n")
        elif self.aggregated.startswith(self.cont):
            self.aggregated = ""
            val = input(self.cont)
            if bool(val):
                stdin.put("    " + input(self.cont) + "\n")
            else:
                stdin.put(input(self.cont) + "\n")
