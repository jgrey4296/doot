##-- imports
from __future__ import annotations
import logging as logmod
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import pathlib as pl
import sys
import sh
import doot
from doot.errors import DootTaskError
from doot._abstract import Action_p
from doot.actions.base_action import DootBaseAction
from doot.structs import DKey, DKeyed

BACKGROUND = DKey("background")
UPDATE     = DKey("update_")
NOTTY      = DKey("notty")
ENV        = DKey("shenv_")

class DootShellBake:

    @DKeyed.args
    @DKeyed.redirects("in_")
    @DKeyed.types("env", fallback=sh, check=sh.Command|bool|None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, args, _in, env, _update):
        if not env:
            env = sh
        try:
            cmd                     = getattr(env, DKey(args[0], explicit=True).expand(spec, state))
            keys                    = [DKey(x, explicit=True) for x in args[1:]]
            expanded                = [x.expand(spec, state, locs=doot.locs) for x in keys]
            match _in.expand(spec, state, fallback=None, check=sh.Command|bool|None):
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


class DootShellBakedRun:

    @DKeyed.redirects("in_")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _in, _update):
        try:
            cmd = _in.expand(spec,state, check=sh.Command|None)
            result = cmd()
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

class DootShellAction(Action_p):
    """
    For actions in subshells.
    all other arguments are passed directly to the program, using `sh`


    can use a pre-baked sh passed into what "shenv_" points to
    """

    @DKeyed.args
    @DKeyed.types("background", "notty", check=bool, fallback=False)
    @DKeyed.types("env", fallback=sh, check=sh.Command|None)
    @DKeyed.paths("cwd", fallback=None, check=pl.Path|None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, args, background, notty, env, cwd, _update) -> dict|bool|None:
        result     = None
        cwd        = cwd or pl.Path.cwd()
        try:
            # Build the command by getting it from env, :
            cmd                     = getattr(env, DKey(args[0], explicit=True).expand(spec, state))
            keys                    = [DKey(x, explicit=True) for x in args[1:]]
            expanded                = [x.expand(spec, state, locs=doot.locs) for x in keys]
            result                  = cmd(*expanded, _return_cmd=True, _bg=background, _tty_out=not notty, _cwd=cwd )
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
            keys     = [DKey(x, explicit=True) for x in args]
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
