#!/usr/bin/env python3
"""


"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv._abstract.protocols import (ActionGrouper_p, ArtifactStruct_p,
                                      Buildable_p, CLIParamProvider_p,
                                      ExecutableTask, Factory_p,
                                      InstantiableSpecification_p, Key_p,
                                      Loader_p, Location_p, Nameable_p,
                                      ParamStruct_p, ProtocolModelMeta,
                                      SpecStruct_p, StubStruct_p,
                                      TomlStubber_p, UpToDate_p,
                                      Persistent_p, Decorator_p
                                      )
from pydantic import BaseModel
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging
