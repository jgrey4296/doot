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
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Job_i
from doot.enums import LocationMeta_f
from doot.structs import TaskSpec, ActionSpec, DKeyed
from doot.task.base_task import DootTask

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer.checkloc")
##-- end logging

make_missing = doot.config.on_fail(False).settings.general.location_check.make_missing()

@doot.check_protocol
class CheckLocsTask(DootTask):
    """ A Task for checking a single location exists

    """
    task_name = "_locations::check"

    def __init__(self, spec=None):
        locations = [doot.locs[f"{{{x}}}"] for x in doot.locs if not doot.locs.metacheck(x, LocationMeta_f.file) and not doot.locs.metacheck(x, LocationMeta_f.remote)]
        actions   = [ActionSpec.build({"args": [x], "fun":self.checklocs }) for x in locations]
        spec      = TaskSpec.build({
            "name"         : CheckLocsTask.task_name,
            "actions"      : actions,
            "priority"     : 100,
        })
        super().__init__(spec)

    @DKeyed.args
    def checklocs(self, spec, state, args):
        exists_p = args[0].exists()
        if exists_p:
            printer.debug("Base Location Exists : %s", spec.args[0])
        else:
            printer.warning("Base Location Missing: %s", spec.args[0])
            if make_missing:
                printer.info("Making Directory: %s", spec.args[0])
                spec.args[0].mkdir(parents=True)
