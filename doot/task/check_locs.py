"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import shutil
from functools import partial
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Maybe
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Job_i
from doot.enums import LocationMeta_e
from doot.structs import TaskSpec, ActionSpec, DKeyed, DKey
from doot.task.base_task import DootTask

# ##-- end 1st party imports

##-- logging
logging   = logmod.getLogger(__name__)
printer   = doot.subprinter()
check_loc = doot.subprinter("check_loc")
##-- end logging

make_missing = doot.config.on_fail(False).startup.location_check.make_missing()
strict       = doot.config.on_fail(True).startup.location_check.strict()

@doot.check_protocol
class CheckLocsTask(DootTask):
    """ A Task for registered directories exist.
    Will build missing if doot.config.startup.location_check.make_missing is true
    """
    task_name = "_locations::check"

    def __init__(self, spec=None):
        locations = [DKey(x, implicit=True) for x in doot.locs]
        actions   = [ActionSpec.build({"args": locations, "fun":self.checklocs })]
        spec      = TaskSpec.build({
            "name"         : CheckLocsTask.task_name,
            "actions"      : actions,
            "priority"     : 100,
        })
        super().__init__(spec)

    @DKeyed.args
    def checklocs(self, spec, state, args):
        errors = []
        for loc in args:
            try:
                if doot.locs.metacheck(loc, LocationMeta_e.file, LocationMeta_e.remote):
                    continue

                path = doot.locs.Current[loc]
                match path.exists():
                    case True:
                        check_loc.trace("Base Location Exists : %s", path)
                    case False if make_missing:
                        check_loc.user("Making Missing Location: %s", path)
                        path.mkdir(parents=True)
                    case False if strict:
                        errors.append(path)
                    case False:
                        check_loc.trace("Base Location Missing: %s", path)
            except PermissionError:
                if strict:
                    errors.append(path)
                check_loc.error("Base Location Permision Error: %s", loc)
        else:
            if strict and bool(errors):
                raise doot.errors.ConfigError("Missing Location(s)", errors)
