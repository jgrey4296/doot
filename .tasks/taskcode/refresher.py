#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

from __future__ import annotations

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

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from marionette_driver.marionette import Marionette

def refresh_firefox(state, spec):
    # Start firefox with: firefox --new-instance -P remote --marionette
    client = Marionette("127.0.0.1")
    client.start_session()
    current = client.current_window_handle
    handles = client.window_handles


    for x in handles:
        client.switch_to_window(x)
        if "127.0.0.1:8000" in client.get_url():
            break
        continue
    else:
        result = client.open("")
        client.switch_to_window(result['handle'])
        client.navigate("http://127.0.0.1:8000")

    client.refresh()


##-- ifmain
if __name__ == "__main__":
    refresh_firefox(None, None)
##-- end ifmain
