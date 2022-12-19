#/usr/bin/env python3
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
from doot.utils.task_group import TaskGroup

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

__all__ = [
]


##-- godot
godot_group = None
if pl.path("project.godot").exists():
    from doot.builders import godot
    godot_group = TaskGroup("godot_group",
                            godot.task_godot_check,
                            godot.task_godot_build,
                            godot.task_godot_debug,
                            godot.task_godot_run,
                            godot.task_godot_script,
                            godot.task_godot_version,
                            godot.task_godot_test,
                            )
##-- end godot

##-- xml
xml_group = None
if bool(list(pl.Path(".").glob("**/*.xml"))):
    from doot.data import xml as xml_reports
    xml_group = TaskGroup("xml_group",
                          xml_reports.XmlSchemaTask(),
                          xml_reports.XmlSchemaVisualiseTask(),
                          xml_reports.XmlValidateTask(),
                          xml_reports.XmlElementsTask(),
                          xml_reports.XmlFormatTask(),
                          xml_reports.XmlPythonSchema(),
                          )
##-- end xml

##-- sqlite
sqlite_group = None
if bool(list(pl.Path(".").glob("**/*.sqlite"))):
    from doot.data import database
    sqlite_group = TaskGroup("sqlite_group",
                             database.SqliteReportTask(),
                             databse.SqlitePrepTask()
                             )

##-- end sqlite

##-- json
json_group = None
if bool(list(pl.Path(".").glob("**/*.sqlite"))):
    from doot.data import json as json_reports
    from doot.docs.plantuml import task_plantuml_json
    json_group = TaskGroup("json group",
                           task_plantuml_json,
                           json_reports.JsonSchemaTask(),
                           )
##-- end json

##-- plantuml
plantuml_group = None
if bool(list(pl.Path(".").glob("**/*.pu"))):
    from doot.docs import plantuml
    plantuml_group = TaskGroup("plantuml_group",
                               plantuml.task_plantuml,
                               plantuml.task_plantuml_text
                               )
##-- end plantuml

##-- csv
csv_group = None
if bool(list(pl.Path(".").glob("**/*.sqlite"))):
    from doot.data import csv_reports
    csv_group = TaskGroup("csv group",
                           csv_reports.CsvVisualiseTask(),
                           csv_reports.CsvSchemaTask(),
                           )
##-- end csv
