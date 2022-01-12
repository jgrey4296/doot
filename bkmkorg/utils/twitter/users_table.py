#!/usr/bin/env python3
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic
from dataclasses import dataclass, field, InitVar
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir

@dataclass
class TwitterUsersWriter:
    """
    Utility class to write twitter users to a simple table file
    """
    _path : str

    CHARWIDTH        = 80

    @property
    def path(self):
        return expanduser(self._path)

    def start(self):
        if exists(self.path):
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
