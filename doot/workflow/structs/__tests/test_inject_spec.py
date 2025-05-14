#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202

# Imports:
# Imports
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from jgdv.structs.dkey import DKey

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from .. import InjectSpec, TaskSpec, TaskName
from ...task import DootTask

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
import typing
from typing import Generic, cast, assert_type, assert_never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if typing.TYPE_CHECKING:
   from jgdv import Maybe
   from typing import Final
   from typing import ClassVar, Any, LiteralString
   from typing import Never, Self, Literal
   from typing import TypeGuard
   from collections.abc import Iterable, Iterator, Callable, Generator
   from collections.abc import Sequence, Mapping, MutableMapping, Hashable

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:

# Body:

class TestInjectSpec:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        match InjectSpec():
            case InjectSpec():
                assert(True)
            case x:
                assert(False), x

    def test_build_none(self):
        match InjectSpec.build({}):
            case None:
                assert(True)
            case x:
                assert(False), x

    def test_build_something(self):
        match InjectSpec.build({"from_spec":["a"]}):
            case InjectSpec():
                assert(True)
            case x:
                assert(False), x

    def test_build_with_bad_rhs_keys(self):
        with pytest.raises(doot.errors.InjectionError):
            InjectSpec.build({"from_spec":{"a":"b"}})

    def test_build_with_bad_lhs_keys(self):
        with pytest.raises(doot.errors.InjectionError):
            InjectSpec.build({"from_spec":{"{a}":"{b}"}})

class TestInjectSpec_Validation:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        inj     = InjectSpec.build({
            "from_spec"   : ["bloo"],
            "from_state"  : [],
            "from_target" : [],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  "bloo": "blah",
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  "bloo": "blah",
                                  })

        match inj.validate(control, target):
            case True:
                assert(True)
            case x:
                 assert(False), x

    def test_pass_redirects(self):
        """
        inject(from_target={bloo:blah})
        v = control[blah]
        target[v] must exist
        """
        inj     = InjectSpec.build({
            "from_spec"   : [],
            "from_state"  : [],
            "from_target" : ["blah"],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  "blah" : "aweg"
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  "aweg": "qqqq",
                                  })

        match inj.validate_details(control, target):
            case dict() as x if not any(bool(v) for v in x.values()):
                assert(True)
            case x:
                assert(False), x


    def test_pass_with_remap(self):
        """
        Checks a mapping of {target <- control}
        """
        inj     = InjectSpec.build({
            "from_spec"   : {"bloo":"{blah}"},
            "from_state"  : [],
            "from_target" : [],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  "blah": 5,
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  "bloo": 5,
                                  })

        match inj.validate_details(control, target):
            case dict() as x if not any(bool(v) for v in x.values()):
                assert(True)
            case x:
                assert(False), x


    def test_pass_tasks(self):
        """
        Checks a mapping of {target <- control}
        """
        inj     = InjectSpec.build({
            "from_spec"   : {"bloo":"{blah}"},
            "from_state"  : [],
            "from_target" : [],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  "blah": 5,
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  "bloo": 5,
                                  })
        control_task = control.make()
        target_task  = target.make()
        match inj.validate_details(control_task, target_task):
            case dict() as x if not any(bool(v) for v in x.values()):
                assert(True)
            case x:
                assert(False), x


    def test_fail_tasks_because_of_state(self):
        """
        Checks a mapping of {target <- control}
        """
        inj     = InjectSpec.build({
            "from_spec"   : {"bloo":"{blah}"},
            "from_state"  : [],
            "from_target" : [],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  "blah": 5,
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  "bloo": 5,
                                  })
        control_task = control.make()
        target_task  = target.make()
        target_task.state['bloo'] = 10
        match inj.validate_details(control_task, target_task):
            case dict() as x if any(bool(v) for v in x.values()):
                assert(True)
            case x:
                assert(False), x


    def test_fail_surplus(self):
        inj     = InjectSpec.build({
            "from_spec"   : ["bloo"],
            "from_state"  : [],
            "from_target" : [],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  "bloo": "blah",
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  })

        match inj.validate_details(control, target):
            case {"lhs_surplus": set() as x } if "bloo" in x:
                assert(True)
            case x:
                assert(False), x

    def test_fail_with_surplus_when_must_inject(self):
        inj     = InjectSpec.build({
            "from_spec"   : ["bloo"],
            "from_state"  : [],
            "from_target" : [],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  "bloo": "blah",
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  "must_inject":["bloo"],
                                  })

        match inj.validate_details(control, target):
            case {"lhs_surplus": set() as x } if bool(x):
                assert(True)
            case x:
                assert(False), x

    def test_fail_missing(self):
        inj     = InjectSpec.build({
            "from_spec"   : ["bloo"],
            "from_state"  : [],
            "from_target" : [],
        })
        control = TaskSpec.build({"name":"basic::control"})
        target  = TaskSpec.build({"name":"basic::target"})

        match inj.validate_details(control, target):
            case {"rhs_missing": set() as x } if "bloo" in x:
                assert(True)
            case x:
                assert(False), x

    def test_fail_rhs_redirects(self):
        """
        inject(from_target={bloo:blah})
        v = control[blah]
        target[v] must exist
        """
        inj     = InjectSpec.build({
            "from_spec"   : [],
            "from_state"  : [],
            "from_target" : ["blah"],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  "aweg": "qqqq",
                                  })

        match inj.validate_details(control, target):
            case {"rhs_redirect": set() as x } if bool(x):
                assert(True)
            case x:
                assert(False), x

    def test_fail_lhs_redirects(self):
        """
        inject(from_target={bloo:blah})
        v = control[blah]
        target[v] doesnt exist
        """
        inj     = InjectSpec.build({
            "from_spec"   : [],
            "from_state"  : [],
            "from_target" : ["blah"],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  "blah": "aweg",
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  })

        match inj.validate_details(control, target):
            case {"lhs_redirect": set() as x } if bool(x):
                assert(True)
            case x:
                assert(False), x


    def test_fail_from_mismatches(self):
        """
        if the specs have the correct structure,
        but not the correct values, fail
        """
        inj     = InjectSpec.build({
            "from_spec"   : ["blah"],
            "from_state"  : [],
            "from_target" : [],
        })
        control = TaskSpec.build({"name":"basic::control",
                                  "blah": "aweg",
                                  })
        target  = TaskSpec.build({"name":"basic::target",
                                  "blah": "not.aweg"
                                  })

        match inj.validate_details(control, target):
            case {"mismatches": set() as x } if bool(x):
                assert(True)
            case x:
                assert(False), x

class TestInjection_Application:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        match InjectSpec.build({"from_spec":["blah"]}):
            case InjectSpec():
                assert(True)
            case x:
                 assert(False), x

    def test_apply_from_spec(self):
        injection = InjectSpec.build({"from_spec":["blah"]})
        control   = TaskSpec.build({"name": "simple::control",
                                    "blah": "bloo"})
        match injection.apply_from_spec(control):
            case {"blah":"bloo"}:
                assert(True)
            case x:
                 assert(False), x

    def test_apply_from_spec_only(self):
        injection = InjectSpec.build({"from_spec":["blah"],
                                      "from_state":["aweg"]})
        control = TaskSpec.build({"name": "simple::control",
                                    "blah": "bloo", "aweg": "other"})
        match injection.apply_from_spec(control):
            case {"aweg": "other"}:
                assert(False)
            case {"blah":"bloo"}:
                assert(True)
            case x:
                 assert(False), x

    def test_apply_from_state(self):
        injection   = InjectSpec.build({"from_state":["aweg"]})
        control = TaskSpec.build({"name": "simple::control",
                                  "aweg": "other"})
        control_task = DootTask(control)
        control_task.state['aweg'] = "task_state"
        match injection.apply_from_state(control_task):
            case {"aweg": "task_state"}:
                assert(True)
            case x:
                assert(False), x

    def test_apply_from_target(self):
        injection   = InjectSpec.build({"from_target":["blah"]})
        control = TaskSpec.build({"name": "simple::control",
                                  "blah": "bloo"})
        match injection.apply_from_spec(control):
            case {"blah_": "bloo"}:
                assert(True)
            case x:
                assert(False), x
