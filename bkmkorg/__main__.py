#/usr/bin/env python3
"""
main access point for all of bkmkorg
"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##-- imports
import cmd
from dataclasses import InitVar, dataclass, field
##-- end imports

@dataclass
class BkmkState:
    """ Data commands use here """
    prompt        : str                            =  field(default="")
    post_cmds     : dict[str, Callable[..., None]] =  field(default_factory=dict)

class BkmkCommand(cmd.Cmd):
    intro                                                   = ""
    prompt                                                  = ""
    _latebind                                               = []
    empty_cmd = "default"

    def __init__(self, *args, **kwargs):
        super(BkmkCommand, self).__init__(*args, **kwargs)
        for inst in self._latebind:
            assert(getattr(inst, "_repl") is None)
            setattr(inst, "_repl", self)

    def default(self, line):
        """ Called when no other command matches """
        pass

    def precmd(self, line) -> str:
        """ For massaging the input command """
        # convert symbols -> cmd names.
        # eg: ':{' -> multi
        try:
            logging.debug("PreCmd Parsing: {}".format(line))
            return line

        except Exception as err:
            logging.warning(f"Pre Parse Failure: {line}")

    def onecmd(self, line):
        try:
            return super(BkmkCommand, self).onecmd(line)
        except Exception as err:
            print(f"\n{err.args[-1]}\n")

    def postcmd(self, stop, line):

        return stop

    def parseline(self, line):
        """Parse the line into a command name and a string containing
        the arguments.  Returns a tuple containing (command, args, line).
        'command' and 'args' may be None if the line couldn't be parsed.
        """
        line = line.strip()

        if not line:
            return None, None, line
        elif line[0] == '?':
            line = 'help ' + line[1:]
        elif line[0] == '!':
            if hasattr(self, 'do_shell'):
                line = 'shell ' + line[1:]
            else:
                return None, None, line

        # split into cmd and args
        i, n = 0, len(line)
        while i < n and line[i] in self.identchars: i = i+1
        cmd, arg = line[:i], line[i:]

        if not self.state.in_multi_line:
            arg = arg.strip()

        return cmd, arg, line

    def emptyline(self):
        """ Overrides default of 'repeat last command',
        and prints the working memory
        """
        return self.onecmd(self.empty_cmd)


    @classmethod
    def register(cls, fn):
        """ Decorator for registering a function into the repl """
        logging.debug(f"{cls.__name__} Registration: {fn.__name__}")
        assert("do_" in fn.__name__)
        assert(fn.__name__ not in dir(cls))
        setattr(cls, fn.__name__, fn)
        return fn

    @classmethod
    def register_class(cls, name):
        """ Register an entire class as the command bound to do_{name},
        (specifically the class' __call__ method)
        """
        def __register(target_cls):
            assert(hasattr(target_cls, "__call__"))
            assert(hasattr(cls, "_latebind"))
            if (not bool(target_cls.__call__.__doc__)) and bool(target_cls.__doc__):
                target_cls.__call__.__doc__ = target_cls.__doc__

            instance = target_cls()
            assert(not hasattr(target_cls, "_repl"))
            setattr(cls, f"do_{name}", instance.__call__)
            setattr(instance, "_repl", None)

            cls._latebind.append(instance)
            return target_cls

        return __register



def main():
    print('TODO')
    # repl = BkmkCommand()
    # repl.cmdloop()



##-- ifmain
if __name__ == '__main__':
    main()
##-- end ifmain
