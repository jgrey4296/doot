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
from doot.utils.toml_accessor import TomlAccessError

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
    "godot_group", "xml_group",
    "sqlite_group", "json_group",
    "plantuml_group", "csv_group",
    "dot_group", "images_group",
]


##-- godot
try:
    from doot.builders import godot
    godot_group = TaskGroup("godot_group",
                            godot.task_godot_check,
                            godot.task_godot_build,
                            godot.task_godot_run,
                            godot.task_godot_version,
                            godot.task_godot_test,
                            )
except TomlAccessError:
    godot_group = None
##-- end godot

##-- xml
try:
    from doot.data import xml as xml_reports
    xml_group = TaskGroup("xml_group",
                          xml_reports.XmlElementsTask(),
                          xml_reports.XmlSchemaTask(),
                          xml_reports.XmlPythonSchemaRaw(),
                          xml_reports.XmlPythonSchemaXSD(),
                          xml_reports.XmlSchemaVisualiseTask(),
                          # xml_reports.XmlValidateTask(),
                          # xml_reports.XmlFormatTask(),
                        )
except TomlAccessError:
    xml_group = None
##-- end xml

##-- sqlite
try:
    from doot.data import database
    sqlite_group = TaskGroup("sqlite_group",
                             database.SqliteReportTask(),
                             database.SqlitePrepTask()
                             )
except TomlAccessError:
    sqlite_group = None
##-- end sqlite

##-- json
try:
    from doot.data import json as json_reports
    # from doot.docs.plantuml import task_plantuml_json
    json_group = TaskGroup("json group",
                           json_reports.JsonPythonSchema(),
                           # task_plantuml_json,
                           # json_reports.JsonSchemaTask(),
                           )
except TomlAccessError:
    json_group = None
##-- end json

##-- plantuml
try:
    from doot.docs import plantuml
    plantuml_group = TaskGroup("plantuml_group",
                               plantuml.task_plantuml,
                               plantuml.task_plantuml_check,
                               plantuml.task_plantuml_text
                               )
except TomlAccessError:
    plantuml_group = None
##-- end plantuml

##-- csv
try:
    from doot.data import csv as csv_reports
    csv_group = TaskGroup("csv group",
                           csv_reports.CSVSummaryTask(),
                           )
except TomlAccessError:
    csv_group = None
##-- end csv

##-- dot
try:
    from doot.docs import dot
    dot_group = TaskGroup("dot group",
                          dot.DotVisualise(),

                          )
except TomlAccessError:
    dot_group = None

##-- end dot

##-- images
try:
    from doot.data import images
    images_group = TaskGroup("images group",
                             images.ImagesListingTask(),
                             images.ImagesHashTask(),

                             )
except TomlAccessError:
    images_group = None
##-- end images
