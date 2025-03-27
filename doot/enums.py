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

from jgdv.mixins.enum_builders import EnumBuilder_m, FlagsBuilder_m
from jgdv.structs.dkey import DKeyMark_e
from jgdv.structs.locator.location import LocationMeta_e

# ##-- 1st party imports
from doot._abstract.control import ExecutionPolicy_e, QueueMeta_e, EdgeType_e
from doot._abstract.task import TaskStatus_e, ActionResponse_e, ArtifactStatus_e
from doot._structs.task_spec import TaskMeta_e
from doot._structs.relation_spec import RelationMeta_e
# ##-- end 1st party imports
