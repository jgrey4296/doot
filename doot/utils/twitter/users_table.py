#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import pathlib as pl
import textwrap
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
##-- end imports

@dataclass
class TwitterUsersWriter:
    """
    Utility class to write twitter users to a simple table file
    """
    _path : pl.Path

    CHARWIDTH        = 80

    @property
    def path(self):
        return self._path.expanduser().resolve()

    def start(self):
        if self.path.exists():
            return

        with open(self.path, 'a') as f:
            f.write("| User ID | Username | Tags | Verified |  Description|\n")
            f.write("|----|\n")

    def add(self, data):
        with open(self.path, 'a') as f:
            for user_str, username, verified, description in data:
                safe_desc = textwrap.wrap(description.replace('|',''), self.CHARWIDTH)
                if not bool(safe_desc):
                    safe_desc = [description]
                f.write("| {} | {} |  | {} | {} |\n".format(user_str,
                                                            username,
                                                            verified,
                                                            safe_desc[0]))
                for subline in safe_desc[1:]:
                    f.write("| | | | | {} |\n".format(subline))
                f.write ("|-----|\n")
