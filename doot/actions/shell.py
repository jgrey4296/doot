##-- imports
from __future__ import annotations
import logging as logmod
##-- end imports

import pathlib as pl
import sys
import sh
import doot
from doot.errors import DootTaskError
from doot._abstract import Action_p
from doot.actions.base_action import DootBaseAction
from doot.structs import DKey, DKeyed

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
fail_l  = doot.subprinter("fail")
##-- end logging

BACKGROUND = DKey("background")
UPDATE     = DKey("update_")
NOTTY      = DKey("notty")
ENV        = DKey("shenv_")

class DootShellBake:
    """
      Create a pre-baked shell command for reuse as in a ShellBakedRun,
      for chaining commands without returning to doot
      args are explicit
    """

    @DKeyed.args
    @DKeyed.redirects("in_")
    @DKeyed.types("env", fallback=None, check=sh.Command|None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, args, _in, env, _update):
        env = env or sh
        try:
            cmd                     = getattr(env, DKey(args[0]).expand(spec, state))
            keys                    = [DKey(x) for x in args[1:]]
            expanded                = [x.expand(spec, state, locs=doot.locs) for x in keys]

            match _in.expand(spec, state, fallback=None, check=sh.Command|bool|None):
                case False | None:
                    baked = cmd.bake(*expanded, _return_cmd=True, _tty_out=False)
                case sh.Command() as x:
                    baked = cmd.bake(*expanded, _in=x(), _return_cmd=True, _tty_out=False)
                case _:
                    raise DootTaskError("Bad pre-command for shell baking", _in)

            return { _update : baked }
        except sh.CommandNotFound as err:
            fail_l.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
        except sh.ErrorReturnCode as err:
            fail_l.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                fail_l.error("%s", err.stdout.decode())

            fail_l.info("")
            if bool(err.stderr):
                fail_l.error("%s", err.stderr.decode())

        return False

class DootShellBakedRun:
    """
      Run a series of baked commands
    """

    @DKeyed.redirects("in_")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _in, _update):
        try:
            cmd    = _in.expand(spec,state, check=sh.Command|None)
            result = cmd()
            return { _update : result }
        except sh.CommandNotFound as err:
            fail_l.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
        except sh.ErrorReturnCode as err:
            fail_l.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                fail_l.error("%s", err.stdout.decode())

            fail_l.info("")
            if bool(err.stderr):
                fail_l.error("%s", err.stderr.decode())

        return False

class DootShellAction(Action_p):
    """
    For actions in subshells/processes.
    all other arguments are passed directly to the program, using `sh`

    can use a pre-baked sh passed into what "shenv_" points to
    """

    @DKeyed.args
    @DKeyed.types("background", "notty", check=bool, fallback=False)
    @DKeyed.types("env", fallback=None, check=sh.Command|None)
    @DKeyed.paths("cwd", fallback=".", check=pl.Path|None)
    @DKeyed.types("exitcodes", fallback=[0])
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, args, background, notty, env, cwd, exitcodes, _update) -> dict|bool|None:
        result     = None
        env        = env or sh
        try:
            # Build the command by getting it from env, :
            cmd_name                = DKey(args[0], fallback=args[0]).expand(spec, state)
            cmd                     = getattr(env, cmd_name)
            keys                    = [DKey(x, mark=DKey.mark.MULTI, fallback=x) for x in args[1:]]
            expanded                = [str(x.expand(spec, state)) for x in keys]
            result                  = cmd(*expanded, _return_cmd=True, _bg=background, _tty_out=not notty, _cwd=cwd )
            if result.exit_code not in exitcodes:
                printer.warning("Shell Command Failed: %s", result.exit_code)
                printer.warning(result.stderr.decode())
                return False

            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, cmd_name, args[1:])
            if not _update:
                printer.info("%s", result, extra={"colour":"reset"})
                return True

            return { _update : result.stdout.decode() }

        except sh.ForkException as err:
            fail_l.error("Shell Command failed: %s", err)
        except sh.CommandNotFound as err:
            fail_l.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
        except sh.ErrorReturnCode as err:
            fail_l.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                fail_l.error("-- Stdout: ")
                fail_l.error("%s", err.stdout.decode())
                fail_l.error("")
                fail_l.error("-- Stdout End")
                fail_l.error("")

            fail_l.info("")
            if bool(err.stderr):
                fail_l.error("-- Stderr: ")
                fail_l.error("%s", err.stderr.decode())
                fail_l.error("")
                fail_l.error("-- Stderr End")
                fail_l.error("")

        return False

class DootInteractiveAction(Action_p):
    """
      An interactive command, which uses the self.interact method as a callback for sh.
    """
    _toml_args = ["background"]
    aggregated = ""
    prompt     = ">>> "
    cont       = "... "

    @DKeyed.formats("prompt", "cont")
    @DKeyed.args
    def __call__(self, spec, state:dict, prompt, cont, args) -> dict|bool|None:
        try:
            cmd      = getattr(env, DKey(args[0], fallback=args[0]).expand(spec, state))
            args     = spec.args[1:]
            keys     = [DKey(x, mark=DKey.mark.MULTI, fallback=x) for x in args[1:]]
            expanded = [str(x.expand(spec, state)) for x in keys]
            result   = cmd(*expanded, _return_cmd=True, _bg=False, _out=self.interact, _out_bufsize=0, _tty_in=True, _unify_ttys=True)
            assert(result.exit_code == 0)
            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, spec.args[0], spec.args[1:])
            printer.info("%s", result, extra={"colour":"reset"})
            return True

        except sh.ForkException as err:
            fail_l.error("Shell Command failed: %s", err)
        except sh.CommandNotFound as err:
            fail_l.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
        except sh.ErrorReturnCode as err:
            fail_l.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                fail_l.error("%s", err.stdout.decode())

            fail_l.info("")
            if bool(err.stderr):
                fail_l.error("%s", err.stderr.decode())

        return False

    def interact(self, char, stdin):
        # TODO possibly add a custom interupt handler/logger
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
