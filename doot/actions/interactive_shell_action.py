##-- imports
from __future__ import annotations
##-- end imports

import sh
import doot
from doot.errors import DootTaskError
from doot._abstract.action import Action_p

class DootInteractiveShellAction(Action_p):
    """
      For interactive actions in subshells
    """

    def __call__(self, *args, **kwargs):
        result = super().execute(*args, **kwargs)

        if isinstance(result, DootTaskError):
            return self.handler(result)

        return result
