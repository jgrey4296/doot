#!/usr/bin/env python3
"""
TEST File updated

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202, B011

# Imports
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
# ##-- end 3rd party imports

##--|
from .. import NullReporter
from .. import _interface as API
##--|

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:

# Body:

class TestNullReporter:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133


    def test_basic(self):
        match NullReporter():
            case API.WorkflowReporter_p() as x:
                assert(isinstance(x, API.GeneralReporter_p))
                assert(True)
            case x:
                assert(False), x


    def test_message(self, caplog):
        logger = logmod.getLogger("simple")
        with caplog.at_level(logmod.DEBUG):
            rep = NullReporter(logger=logger)
            rep.active_level(logmod.DEBUG)
            rep._out("wait", info="blah", msg="bloo")

        assert("[blah]" in caplog.text)
        assert("bloo" in caplog.text)

    ##--|

    @pytest.mark.skip
    def test_todo(self):
        pass
