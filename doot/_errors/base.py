#!/usr/bin/env python3
"""



"""
# Import:
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)

# ##-- end stdlib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Global Vars:

# Body:
class DootError(Exception):
    """
      The base class for all Doot Errors
      will try to % format the first argument with remaining args in str()
    """
    general_msg = "Non-Specific Doot Error:"

    def __str__(self):
        try:
            return self.args[0] % self.args[1:]
        except TypeError:
            return str(self.args)


class BackendError(DootError):
    pass

class FrontendError(DootError):
    pass

class UserError(DootError):
    pass
