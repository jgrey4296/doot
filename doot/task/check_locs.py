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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.structs.dkey import DKeyed, DKey
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.enums import LocationMeta_e
from doot.structs import ActionSpec
from doot.task.core.task import DootTask

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from doot.structs import TaskSpec
from doot._abstract import Task_p

# isort: on
# ##-- end types

##-- logging
logging   = logmod.getLogger(__name__)
##-- end logging

make_missing = doot.config.on_fail(False).startup.location_check.make_missing()
strict       = doot.config.on_fail(True).startup.location_check.strict()
##--|
@Proto(Task_p)
class CheckLocsTask(DootTask):
    """ A Task for registered directories exist.
    Will build missing if doot.config.startup.location_check.make_missing is true
    """
    task_name = "_locations::check"

    def __init__(self, spec:TaskSpec=None):
        match [DKey(x, implicit=True) for x in doot.locs]:
            case []:
                actions = []
            case [*_]:
                locations = [DKey(x, implicit=True) for x in doot.locs]
                actions   = [ActionSpec.build({"args": locations, "fun":self.checklocs })]

        spec      = TaskSpec.build({
            "name"         : CheckLocsTask.task_name,
            "actions"      : actions,
            "priority"     : 100,
        })
        super().__init__(spec)

    @DKeyed.args
    def checklocs(self, spec:ActionSpec, state:dict, args:list) -> None:
        errors = []
        for loc in args:
            try:
                if doot.locs.metacheck(loc, LocationMeta_e.file, LocationMeta_e.remote):
                    continue

                path = doot.locs.Current[loc]
                match path.exists():
                    case True:
                        logging.detail("Location Exists : %s", path)
                    case False if make_missing:
                        doot.report.act(info="Check", msg=f"Making Missing Location: {path}")
                        path.mkdir(parents=True)
                    case False if strict:
                        errors.append(path)
                    case False:
                        doot.report.act(info="Check", msg=f"Location Missing: {path}")
            except PermissionError:
                if strict:
                    errors.append(path)
                doot.report.act("Check", "Location Permision Error: %s", loc)
                doot.report.fail()
        else:
            if strict and bool(errors):
                raise doot.errors.ConfigError("Missing Location(s)", errors)
