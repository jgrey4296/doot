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
from jgdv.cli._interface import ParseReport_d, ParseResult_d
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

class TestOverlord_Startup:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic_ctor(self):
        match DootOverlord():
            case DootOverlord() as do:
                assert(True)
            case x:
                assert(False), x

    def test_null_setup(self):
        obj = DootOverlord()
        assert(bool(obj.constants))
        assert(bool(obj.aliases))

    @pytest.mark.filterwarnings("ignore")
    def test_load_config_default(self, mocker):
        do              = DootOverlord()
        default_config  = API.template_path / do.constants.paths.TOML_TEMPLATE
        do.setup(targets=[default_config])
        assert(do.is_setup)
        assert(bool(do.config))
        do.verify_config_version(do.config.startup.doot_version, source="testing")
        assert(True)

    @pytest.mark.filterwarnings("ignore")
    def test_loc_init(self, mocker):
        do  = DootOverlord()
        default_config  = API.template_path / do.constants.paths.TOML_TEMPLATE
        assert(not bool(do.locs))
        do.setup(targets=[default_config])
        assert(do.is_setup)
        assert(bool(do.config))
        assert(bool(do.locs))

class TestOverlord_VersionCheck:
    """
    Test the version checking used for config file and task specs
    """

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    @pytest.mark.parametrize("ver", ["1.1.0", "1.1.5", "1.1.15"])
    def test_with_override(self, ver):
        target = "1.1"
        do = DootOverlord()
        do.verify_config_version(ver, None, override=target)
        assert(True)

    @pytest.mark.parametrize("ver", ["1.0.0", "1.0.5", "1.0.15"])
    def test_with_override_fail(self, ver):
        target = "1.1"
        do = DootOverlord()
        with pytest.raises(doot.errors.VersionMismatchError):
            do.verify_config_version(ver, None, override=target)

    def test_verify_config_version(self):
        do = DootOverlord()
        do.verify_config_version(do.__version__, "test")
        assert(True)

    def test_verify_config_version_fail(self):
        do = DootOverlord()
        with pytest.raises(doot.errors.VersionMismatchError):
            do.verify_config_version("0.1.1", "test")

class TestOverlord_WorkflowUtil:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_update_global_task_state_default(self):
        do = DootOverlord()
        assert(not bool(do.global_task_state))

    def test_update_global_task_state_empty_data(self):
        do = DootOverlord()
        assert(not bool(do.global_task_state))
        do.update_global_task_state(ChainGuard(), source="testing")
        assert(not bool(do.global_task_state))

    def test_update_global_task_with_data(self):
        do = DootOverlord()
        assert(not bool(do.global_task_state))
        data = ChainGuard({API.GLOBAL_STATE_KEY: {"testval": "blah"}})
        do.update_global_task_state(data, source="testing")
        assert(bool(do.global_task_state))
        assert(do.global_task_state['testval'] == "blah")

    def test_update_global_task_state_multi(self):
        do = DootOverlord()
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
        do = DootOverlord()
        assert(not bool(do.global_task_state))
        data1 = ChainGuard({API.GLOBAL_STATE_KEY: {"testval1": "blah"}})
        data2 = ChainGuard({API.GLOBAL_STATE_KEY: {"testval1": "bloo"}})
        do.update_global_task_state(data1, source="testing")
        with pytest.raises(doot.errors.GlobalStateMismatch):
            do.update_global_task_state(data2, source="testing")


class TestOverlord_cmd_args:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_set_parsed_cli_args_empty(self):
        do      = DootOverlord()
        report  = ParseReport_d(raw=[], remaining=[], _help=False,
                                prog=ParseResult_d("prog", args={}, ref=None),
                               )
        assert(not bool(do.args))
        do.update_cmd_args(report)
        assert(bool(do.args))


    def test_set_parsed_cli_args_prog(self):
        do      = DootOverlord()
        report  = ParseReport_d(raw=[], remaining=[], _help=False,
                               prog=ParseResult_d("prog", args={"blah":2}, ref=None),
                               )
        assert(not bool(do.args))
        do.update_cmd_args(report)
        assert(bool(do.args))
        assert(do.args.prog.args.blah == 2)


    def test_set_parsed_cli_args_cmds(self):
        do      = DootOverlord()
        report  = ParseReport_d(raw=[], remaining=[], _help=False,
                               prog=ParseResult_d("prog", args={}, ref=None),
                               )
        report.cmds['blah'] = (ParseResult_d(name="blah", args={"aweg":2}), )
        assert(not bool(do.args))
        do.update_cmd_args(report)
        assert(bool(do.args))
        assert(do.args.cmds.blah[0].args.aweg== 2)


    def test_set_parsed_args_subs(self):
        do      = DootOverlord()
        report  = ParseReport_d(raw=[], remaining=[], _help=False,
                               prog=ParseResult_d("prog", args={}, ref=None),
                               )
        report.subs['blah'] = (ParseResult_d(name="blah", args={"aweg":2}), )
        assert(not bool(do.args))
        do.update_cmd_args(report)
        assert(bool(do.args))
        assert(do.args.subs.blah[0].args.aweg== 2)
