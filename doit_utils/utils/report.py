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

##-- reports

## TODO bash -ic "conda list --export > ./conda_env.txt"
## TODO conda env export --from-history > env.yaml

# TODO class / line reports
def task_line_report():
    find_cmd = build_cmd("find",
                         [src_dir, "-name", '"*.py"',
                          "-not", "-name", '"test_*.py"',
                          "-not", "-name", '"*__init__.py"',
                          "-print0"])
    line_cmd = build_cmd("xargs", ["-0", "wc", "-l"])
    sort_cmd = build_cmd("sort", [])

    target = build_dir / "linecounts.report"

    return {
        "basename"  : "line-report",
        "actions"   : [ f"{find_cmd} | {line_cmd} | {sort_cmd} > {target}" ],
        "targets"   : [ target ],
        "task_dep"  : ["_base-dircheck"],
        "clean"     : True,
        "verbosity" : 2,
    }

# find {top} -name "*.py" -not -name "flycheck*" | xargs awk '/^class/ {print $0}' > class.report
##-- end reports
