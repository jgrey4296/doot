#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202

# Imports
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from jgdv.structs.chainguard import ChainGuard
# ##-- end 3rd party imports

import doot._interface as API
import doot.errors
from doot.control.overlord import DootOverlord

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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
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

class TestOverlord:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        match DootOverlord():
            case DootOverlord():
                assert(True)
            case x:
                assert(False), x

class TestOverlordStartup:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_constants(self):
        match DootOverlord(force_new=True):
            case DootOverlord() as do:
                assert(bool(do.constants))
            case x:
                assert(False), x

    def test_aliases(self):
        match DootOverlord(force_new=True):
            case DootOverlord() as do:
                assert(bool(do.aliases))
                assert(not bool(do.cmd_aliases))
            case x:
                assert(False), x

    def test_null_setup_config(self):
        match DootOverlord(force_new=True):
            case DootOverlord() as do:
                assert(not bool(do.config))
            case x:
                assert(False), x

    @pytest.mark.filterwarnings("ignore")
    def test_load_config_default(self, mocker):
        do = DootOverlord(force_new=True)
        default_config = API.template_path / do.constants.paths.TOML_TEMPLATE
        do.setup(targets=[default_config])
        assert(bool(do.config))
        do.verify_config_version(do.config.startup.doot_version, source="testing")
        assert(True)

    @pytest.mark.filterwarnings("ignore")
    def test_loc_init(self, mocker):
        do = DootOverlord(force_new=True)
        assert(not bool(do.locs))
        do.setup()
        assert(bool(do.locs))


class TestOverlordLogging:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

class TestOverlordWorkflowUtil:

    def test_verify_config_version(self):
        do = DootOverlord()
        do.verify_config_version(do.__version__, "test")
        assert(True)

    def test_verify_config_version_fail(self):
        do = DootOverlord()
        with pytest.raises(doot.errors.VersionMismatchError):
            do.verify_config_version("0.1.1", "test")

    def test_update_global_task_state_default(self):
        do = DootOverlord(force_new=True)
        assert(not bool(do.global_task_state))

    def test_update_global_task_state_empty_data(self):
        do = DootOverlord(force_new=True)
        assert(not bool(do.global_task_state))
        do.update_global_task_state(ChainGuard(), source="testing")
        assert(not bool(do.global_task_state))

    def test_update_global_task_with_data(self):
        do = DootOverlord(force_new=True)
        assert(not bool(do.global_task_state))
        data = ChainGuard({API.GLOBAL_STATE_KEY: {"testval": "blah"}})
        do.update_global_task_state(data, source="testing")
        assert(bool(do.global_task_state))
        assert(do.global_task_state['testval'] == "blah")

    def test_update_global_task_state_multi(self):
        do = DootOverlord(force_new=True)
        assert(not bool(do.global_task_state))
        data1 = ChainGuard({API.GLOBAL_STATE_KEY: {"testval1": "blah"}})
        data2 = ChainGuard({API.GLOBAL_STATE_KEY: {"testval2": "bloo"}})
        do.update_global_task_state(data1, source="testing")
        assert(bool(do.global_task_state))
        assert(do.global_task_state['testval1'] == "blah")
        assert("testval2" not in do.global_task_state)
        do.update_global_task_state(data2, source="testing")
        assert(do.global_task_state['testval1'] == "blah")
        assert(do.global_task_state['testval2'] == "bloo")

    def test_update_global_task_state_conflict(self):
        do = DootOverlord(force_new=True)
        assert(not bool(do.global_task_state))
        data1 = ChainGuard({API.GLOBAL_STATE_KEY: {"testval1": "blah"}})
        data2 = ChainGuard({API.GLOBAL_STATE_KEY: {"testval1": "bloo"}})
        do.update_global_task_state(data1, source="testing")
        with pytest.raises(doot.errors.GlobalStateMismatch):
            do.update_global_task_state(data2, source="testing")

    def test_set_parsed_cli_args(self):
        do = DootOverlord(force_new=True)
        assert(not bool(do.args))
        do.set_parsed_cli_args(ChainGuard({"blah": True}))
        assert(bool(do.args))

class TestOverlordSingleton:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_is_singleton(self):
        do1 = DootOverlord()
        do2 = DootOverlord()
        assert(do1 is do2)

    def test_force_new(self):
        do1 = DootOverlord()
        do2 = DootOverlord(force_new=True)
        assert(do1 is not do2)
