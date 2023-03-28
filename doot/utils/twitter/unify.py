#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

def copy_files(source_dir:pl.Path, target_dir:pl.Path):
    logging.info("Copying from %s to %s", source_dir, target_dir)
    if source_dir.exists() and not target_dir.exists():
        logging.info("as group")
        result = run(['cp' ,'-r', str(source_dir), str(target_dir)], capture_output=True, check=True)
    elif target_dir.exists():
        logging.info("as individual")
        for y in source_dir.iterdir():
            if not y.is_file():
                continue

            call_sig = ['cp', str(y), str(target_dir / y.name)]
            run(call_sig, capture_output=True, check=True)

def copy_new(source:pl.Path, lib_path:pl.Path):
    logging.info("Adding to library with: %s", source)
    file_dir  = source.parent / f"{source.stem}_files"

    first_letter = source.name[0].lower()
    if not ("a" <= first_letter <= "z"):
        first_letter = "symbols"

    target_for_new = lib_path / f"group_{first_letter}"

    if not (target_for_new / source.name).exists():
        run(['cp', str(source), str(target_for_new)], capture_output=True, check=True)

    run(["mv", str(source), str(source.parent / f"{source.name}{PROCESSED}")], capture_output=True, check=True)

    copy_files(file_dir, target_for_new / f"{source.stem}_files")

def integrate(source:pl.Path, lib_dict:dict[str,Any]):
    logging.info("Integrating: %s", source)
    new_files      = source.parent / f"{source.stem}_files"
    existing_org   = lib_dict[source.name] /  source.name
    existing_files = lib_dict[source.name] / f"{source.stem}_files"

    assert(existing_org.exists())
    if not existing_files.exists():
        existing_files.mkdir()

    with open(source, 'r') as f:
        lines = f.read()

    with open(existing_org, 'a') as f:
        f.write("\n")
        f.write(lines)

    run(["mv", str(source), str(source.parent / f"{source.name}{PROCESSED}")], capture_output=True, check=True)

    if not new_files.exists():
        return

    copy_files(new_files, existing_files)

# def update_record(path:pl.Path, sources:List[pl.Path]):
#     now : str = datetime.datetime.now().strftime("%Y-%m-%d")

#     all_ids = get_all_tweet_ids(*sources, ext=".org_processed")

#     # add it to the library record
#     with open(path, 'a') as f:
#         # Insert date
#         f.write(f"{now}:\n\t")
#         f.write("\n\t".join(sorted(all_ids)))
#         f.write("\n----------------------------------------\n")
