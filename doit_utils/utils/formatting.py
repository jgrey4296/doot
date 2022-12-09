##-- imports
from __future__ import annotations
import pathlib as pl
import shutil

from doit import create_after
from doit.action import CmdAction
from doit.tools import (Interactive, PythonInteractiveAction, create_folder,
                        set_trace)

try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml
##-- end imports

# code
# bibtex
