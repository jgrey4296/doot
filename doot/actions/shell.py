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
class DootShellBake:

    @DootKey.kwrap.args
    @DootKey.kwrap.types("in_", hint={"on_fail":None, "type_":sh.Command|bool|None})
    @DootKey.kwrap.types("env", hint={"on_fail":sh, "type_":sh.Command|bool|None})
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, args, _in, env, _update):
        if not env:
            env = sh
        try:
            cmd                     = getattr(env, DootKey.make(args[0], explicit=True).expand(spec, state))
            keys                    = [DootKey.make(x, explicit=True) for x in args[1:]]
            expanded                = [x.expand(spec, state, locs=doot.locs) for x in keys]
            match _in:
                case False | None:
                    baked = cmd.bake(*expanded, _return_cmd=True, _tty_out=False)
                case sh.Command():
                    baked = cmd.bake(*expanded, _in=_in(), _return_cmd=True, _tty_out=False)
                case _:
                    raise DootTaskError("Bad pre-command for shell baking", _in)

            return { _update : baked }
        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
        except sh.ErrorReturnCode as err:
            printer.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                printer.error("%s", err.stdout.decode())

            printer.info("")
            if bool(err.stderr):
                printer.error("%s", err.stderr.decode())

        return False


@doot.check_protocol
class DootShellBakedRun:

    @DootKey.kwrap.types("in_", hint={"on_fail":None, "type_":sh.Command|None})
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, _in, _update):
        try:
            result = _in()
            return { _update : result }
        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
        except sh.ErrorReturnCode as err:
            printer.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                printer.error("%s", err.stdout.decode())

            printer.info("")
            if bool(err.stderr):
                printer.error("%s", err.stderr.decode())

        return False

@doot.check_protocol
class DootShellAction(Action_p):
    """
    For actions in subshells.
    all other arguments are passed directly to the program, using `sh`


    can use a pre-baked sh passed into what "shenv_" points to
    """

    @DootKey.kwrap.args
    @DootKey.kwrap.types("background", "notty", hint={"type_":bool, "on_fail":False})
    @DootKey.kwrap.types("env", hint={"on_fail":sh, "type_":sh.Command|None})
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, args, background, notty, env, _update) -> dict|bool|None:
        result     = None
        try:
            # Build the command by getting it from env, :
            cmd                     = getattr(env, DootKey.make(args[0], explicit=True).expand(spec, state))
            keys                    = [DootKey.make(x, explicit=True) for x in args[1:]]
            expanded                = [x.expand(spec, state, locs=doot.locs) for x in keys]
            result                  = cmd(*expanded, _return_cmd=True, _bg=background, _tty_out=notty)
            assert(result.exit_code == 0)

            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, args[0], args[1:])
            if not _update:
                printer.info("%s", result, extra={"colour":"reset"})
                return True

            return { _update : result.stdout }

        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
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
            expanded = [x.expand(spec, state, locs=doot.locs) for x in keys]
            result   = cmd(*expanded, _return_cmd=True, _bg=spec.kwargs.on_fail(False, bool).background(), _out=self.interact, _out_bufsize=0, _tty_in=True, _unify_ttys=True)
            assert(result.exit_code == 0)
            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, spec.args[0], spec.args[1:])
            printer.info("%s", result, extra={"colour":"reset"})
            return True
        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], spec.args)
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
