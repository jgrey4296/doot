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
import shutil
from functools import partial
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.structs.dkey import DKey, DKeyed
from jgdv.structs.locator._interface import LocationMeta_e

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

# ##-| Local
from . import ActionSpec, DootTask, TaskSpec

# # End of Imports.

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
    import pathlib as pl
    from .interface import TaskSpec_i, ActionSpec_i
    from jgdv.structs.locator._interface import Location_p
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from ._interface import Task_p

# isort: on
# ##-- end types

##-- logging
logging   = logmod.getLogger(__name__)
##-- end logging

make_missing : Final[bool] = doot.config.on_fail(False).settings.commands.run.location_check.make_missing()  # noqa: FBT003
strict       : Final[bool] = doot.config.on_fail(True).settings.commands.run.location_check.strict()  # noqa: FBT003
##--|
@Proto(Task_p)
class CheckLocsTask(DootTask):
    """ A Task for registered directories exist.
    Will build missing if doot.config.startup.location_check.make_missing is true
    """
    task_name = "_locations::check"

    def __init__(self, spec:TaskSpec_i=None):
        actions : list[ActionSpec_i]
        locations : list[Location_p]
        match [DKey(x, implicit=True) for x in doot.locs]:
            case []:
                actions = []
            case [*_]:
                locations = [DKey(x, implicit=True) for x in doot.locs] # type: ignore[misc]
                actions   = [ActionSpec.build({"args": locations, "fun":self.checklocs })]

        spec      = {
            "name"         : CheckLocsTask.task_name,
            "actions"      : actions,
            "priority"     : 100,
        }
        super().__init__(TaskSpec(**spec))

    @DKeyed.args # type: ignore[attr-defined]
    def checklocs(self, spec:ActionSpec_i, state:dict, args:list) -> None:  # noqa: ARG002
        path : pl.Path
        ##--|
        errors  = []
        for loc in args:
            try:
                if doot.locs.metacheck(loc, LocationMeta_e.file, LocationMeta_e.remote):
                    continue

                path = doot.locs.Current[loc]
                match path.exists():
                    case True:
                        logging.debug("Location Exists : %s", path)
                    case False if make_missing:
                        doot.report.wf.act(info="Check", msg=f"Making Missing Location: {path}")
                        path.mkdir(parents=True)
                    case False if strict:
                        errors.append(path)
                    case False:
                        doot.report.wf.act(info="Check", msg=f"Location Missing: {path}")
            except PermissionError:
                if strict:
                    errors.append(path)
                doot.report.wf.act("Check", f"Location Permision Error: {loc}")
                doot.report.wf.fail()
        else:
            if strict and bool(errors):
                raise doot.errors.ConfigError("Missing Location(s)", errors)
