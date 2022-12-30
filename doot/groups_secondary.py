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
from doot.utils.toml_access import TomlAccessError, TomlAccess
from doot import build_dir, data_toml, temp_dir, doc_dir, src_dir, gen_dir

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
    data_toml.tool.doot.godot
    from doot.builders import godot
    godot_group = TaskGroup("godot_group",
                            godot.GodotCheckTask([pl.Path()]),
                            godot.GodotBuild(build_dir),
                            godot.GodotRun(build_dir, ""),
                            godot.GodotRunScene([pl.Path()]),
                            godot.task_godot_version,
                            godot.task_godot_test,
                            )
except TomlAccessError:
    godot_group = None
##-- end godot

##-- xml
try:
    data_toml.tool.doot.xml
    xml_data_dirs = [pl.Path(x) for x in data_toml.or_get([]).tool.doot.xml.data_dirs() if pl.Path(x).exists()]
    xml_gen_dir   = gen_dir
    xml_build_dir = build_dir     / "xml"
    schema_dir    = xml_build_dir / "schema"
    elements_dir  = xml_build_dir / "elements"
    visual_dir    = xml_build_dir / "visual"
    from doot.data import xml as xml_reports
    xml_reports.build_xml_checks()
    xml_group = TaskGroup("xml_group",
                          xml_reports.XmlElementsTask(xml_data_dirs], elements_dir),
                          xml_reports.XmlSchemaTask(xml_data_dirs, schema_dir),
                          xml_reports.XmlPythonSchemaRaw(xml_data_dirs, xml_gen_dir]),
                          xml_reports.XmlPythonSchemaXSD(xml_data_dirs + [schema_dir], xml_gen_dir),
                          xml_reports.XmlSchemaVisualiseTask(xml_data_dirs + [schema_dir], visual_dir),
                          xml_reports.XmlFormatTask(xml_data_dirs),
                        )
except TomlAccessError:
    xml_group = None
##-- end xml

##-- sqlite
try:
    data_toml.tool.doot.databse
    from doot.data import database
    sqlite_dir = build_dir / "sqlite"
    database.build_sqlite_check(sqlite_dir)
    sqlite_group = TaskGroup("sqlite_group",
                             database.SqliteReportTask([src_dir]),
                             database.SqlitePrepTask([src_dir], sqlite_dir)
                             )
except TomlAccessError:
    sqlite_group = None
##-- end sqlite

##-- json
try:
    data_toml.tool.doot.json
    from doot.data import json as json_reports
    data_dirs = [pl.Path(x) for x in data_toml.or_get([]).tool.doot.json.data_dirs() if pl.Path(x).exists()]
    json_gen_dir   = gen_dir
    json_build_dir = build_dir / "json"
    visual_dir     = json_build_dir   / "visual"
    # from doot.docs.plantuml import task_plantuml_json
    json_group = TaskGroup("json group",
                           json_reports.JsonPythonSchema(data_dirs]),
                           json_reports.JsonFormatTask(data_dirs, json_gen_dir),
                           json_reports.JsonVisualise(data_dirs, visual_dir)
                           # task_plantuml_json,
                           # json_reports.JsonSchemaTask(),
                           )
except TomlAccessError:
    json_group = None
##-- end json

##-- plantuml
try:
    data_toml.tool.doot.plantuml
    plant_dir = build_dir / "plantuml"
    from doot.docs import plantuml
    plantuml.build_plantuml_checks(plant_dir)
    plantuml_group = TaskGroup("plantuml_group",
                               plantuml.PlantUMLGlobberTask([build_dir], plant_dir),
                               plantuml.PlantUMLGlobberTask([build_dir], plant_dir, fmt="txt"),
                               plantuml.PlantUMLGlobberCheck([build_dir]),
                               )
except TomlAccessError:
    plantuml_group = None
##-- end plantuml

##-- csv
try:
    data_toml.tool.doot.csv
    csv_dir = build_dir / "csv"
    from doot.data import csv as csv_reports
    csv_group = TaskGroup("csv group",
                          csv_reports.CSVSummaryTask([src_dir], csv_dir),
                          csv_reports.CSVSummaryXMLTask([src_dir], csv_dir),
                           )
except TomlAccessError:
    csv_group = None
##-- end csv

##-- dot
try:
    data_toml.tool.doot.dot
    dot_build_dir = build_dir / "dot"
    visual_dir    = dot_build_dir   / "visual"
    from doot.docs import dot
    dot.build_dot_checks(dot_build_dir, visual_dir)
    dot_group = TaskGroup("dot group",
                          dot.DotVisualise([dot_build_dir], visual_dir, ext="png"),

                          )
except TomlAccessError:
    dot_group = None

##-- end dot

##-- images
try:
    data_toml.tool.doot.images
    data_dirs        = [pl.Path(x) for x in data_toml.or_get([]).tool.doot.images.data_dirs() if pl.Path(x).exists()]
    exts : list[str] = data_toml.or_get([".jpg"]).tool.doot.images.exts()
    images_build_dir = build_dir / "images"
    from doot.data import images
    images.build_images_dir(images_build_dir)
    images_group = TaskGroup("images group",
                             images.ImagesListingTask(data_dirs, images_build_dir),
                             images.ImagesHashTask(data_dirs, images_build_dir),

                             )
except TomlAccessError:
    images_group = None
##-- end images
