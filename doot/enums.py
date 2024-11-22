#!/usr/bin/env python3
"""
These are the core enums and flags used to easily convey information around doot.
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import enum
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)

# ##-- end stdlib imports

from jgdv.enums.util import EnumBuilder_m, FlagsBuilder_m

# ##-- 1st party imports
from doot._abstract.control import ExecutionPolicy_e, QueueMeta_e, EdgeType_e
from doot._abstract.task import TaskStatus_e, ActionResponse_e, ArtifactStatus_e
from doot._abstract.reporter import Report_f
from doot._abstract.key import DKeyMark_e
from doot._structs.task_name import TaskMeta_f
# ##-- end 1st party imports

class RelationMeta_e(enum.Enum):
    """
      What types+synonyms of task relation there can be,
      in the form Obj {rel} Y,

      eg: cake dependsOn baking.
      or: baking requirementFor cake.
      or: eatingCake conflictsWith givingCake
    """
    needs            = enum.auto()
    blocks           = enum.auto()
    # excludes         = enum.auto()

    default          = needs


class LocationMeta_f(FlagsBuilder_m, enum.Flag):
    """ Available metadata attachable to a location """

    abstract     = enum.auto()
    artifact     = enum.auto()
    directory    = enum.auto()
    cleanable    = enum.auto()
    normOnLoad   = enum.auto()
    protected    = enum.auto()
    glob         = enum.auto()
    expandable   = enum.auto()
    remote       = enum.auto()

    # Aliases
    file         = artifact
    location     = directory
    indefinite   = abstract

    default      = directory
