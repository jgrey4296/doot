#!/usr/bin/env python3
"""
The main access point for protocols.
Most are imported from jgdv._abstract.protocols

"""

# Imports:
from __future__ import annotations

# ##-- 3rd party imports
from jgdv._abstract.protocols import (ActionGrouper_p, ArtifactStruct_p,
                                      Buildable_p,
                                      ExecutableTask, Factory_p,
                                      InstantiableSpecification_p,
                                      Loader_p, Nameable_p,
                                      SpecStruct_p, StubStruct_p,
                                      TomlStubber_p, UpToDate_p,
                                      Persistent_p,
                                      )
from jgdv._abstract.pydantic_proto import ProtocolModelMeta
from jgdv.structs.dkey import Key_p
from jgdv.structs.locator import Location_p
from jgdv.cli import CLIParamProvider_p, ParamStruct_p
from jgdv.decorators import Decorator_p
from pydantic import BaseModel
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports
