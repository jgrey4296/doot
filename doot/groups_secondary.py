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
from doot import data_toml, doot_dirs

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
    godot_dirs = doot_dirs.extend(prefix="godot", _src="")
    godot_dirs.add_extra({ "scenes" : godot_dirs.src / "scenes",
                         })
    godot_group = TaskGroup("godot_group",
                            godot.GodotCheckTask(godot_dirs, [godot_dirs.src]),
                            godot.GodotBuild(godot_dirs),
                            godot.GodotRunScene(godot_dirs, [godot_dirs.src]),
                            godot.GodotRunScript(godot_dirs, [godot_dirs.src]),
                            godot.task_godot_version,
                            godot.task_godot_test,
                            godot.task_newscene(godot_dirs),
                            )
except TomlAccessError:
    godot_group = None
##-- end godot

##-- xml
try:
    data_toml.tool.doot.xml
    xml_dirs = doot_dirs.extend(prefix="xml")
    xml_dirs.add_extra({"visual": xml_dirs.docs / "visual",
                        "elements" : xml_dirs.build / "elements",
                        "schema"    : xml_dirs.build / "schema",

                        })
    xml_data_dirs = [xml_dirs.data] + [pl.Path(x) for x in data_toml.or_get([]).tool.doot.xml.data_dirs() if pl.Path(x).exists()]
    from doot.data import xml as xml_reports
    xml_group = TaskGroup("xml_group",
                          xml_reports.XmlElementsTask(xml_dirs, xml_data_dirs),
                          xml_reports.XmlSchemaTask(xml_dirs, xml_data_dirs),
                          xml_reports.XmlPythonSchemaRaw(xml_dirs, xml_data_dirs),
                          xml_reports.XmlPythonSchemaXSD(xml_dirs, xml_data_dirs),
                          xml_reports.XmlSchemaVisualiseTask(xml_dirs, xml_data_dirs),
                          xml_reports.XmlFormatTask(xml_dirs, xml_data_dirs),
                        )
except TomlAccessError:
    xml_group = None
##-- end xml

##-- sqlite
try:
    data_toml.tool.doot.databse
    from doot.data import database
    sqlite_dirs  = doot_dirs.extend(prefix="sqlite")
    sqlite_group = TaskGroup("sqlite_group",
                             database.SqliteReportTask(sqlite_dirs),
                             database.SqlitePrepTask(sqlite_dirs),
                             )
except TomlAccessError:
    sqlite_group = None
##-- end sqlite

##-- json
try:
    data_toml.tool.doot.json
    from doot.data import json as json_reports
    data_dirs = [pl.Path(x) for x in data_toml.or_get([]).tool.doot.json.data_dirs() if pl.Path(x).exists()]
    json_dirs = doot_dirs.extend(prefix="json")
    # from doot.docs.plantuml import task_plantuml_json
    json_group = TaskGroup("json group",
                           json_reports.JsonPythonSchema(data_dirs),
                           json_reports.JsonFormatTask(data_dirs, json_gen_dir),
                           json_reports.JsonVisualise(data_dirs, visual_dir),
                           # task_plantuml_json,
                           # json_reports.JsonSchemaTask(),
                           )
except TomlAccessError:
    json_group = None
##-- end json

##-- plantuml
try:
    data_toml.tool.doot.plantuml
    from doot.docs import plantuml
    plant_dirs = doot_dirs.extend(prefix="plantuml", _src="docs/visual")
    plantuml_group = TaskGroup("plantuml_group",
                               plantuml.PlantUMLGlobberTask(dirs, [plant_dirs.src], plant_dir),
                               plantuml.PlantUMLGlobberTask(dirs, [plant_dirs.src], plant_dir, fmt="txt"),
                               plantuml.PlantUMLGlobberCheck(dirs, [plant_dirs.src]),
                               )
except TomlAccessError:
    plantuml_group = None
##-- end plantuml

##-- csv
try:
    data_toml.tool.doot.csv
    csv_dirs = doot_dirs.extend(prefix="csv")
    from doot.data import csv as csv_reports
    csv_group = TaskGroup("csv group",
                          csv_reports.CSVSummaryTask(csv_dirs, [csv_dirs.data]),
                          csv_reports.CSVSummaryXMLTask(csv_dirs, [csv_dirs.data], csv_dir),
                           )
except TomlAccessError:
    csv_group = None
##-- end csv

##-- dot
try:
    data_toml.tool.doot.dot
    dot_dirs = doot_dirs.extend(prefix="dot", _src="docs/visual")
    from doot.docs import dot
    dot_group = TaskGroup("dot group",
                          dot.DotVisualise(dot_dirs, [dot_dirs.src]),
                          )
except TomlAccessError:
    dot_group = None

##-- end dot

##-- images
try:
    data_toml.tool.doot.images
    image_dirs  = doot_dirs.extend(prefix="images")
    image_roots = [pl.Path(x) for x in data_toml.or_get([]).tool.doot.images.data_dirs() if pl.Path(x).exists()]
    from doot.data import images
    images_group = TaskGroup("images group",
                             images.HashImages(image_dirs, image_roots),
                             images.TesseractGlobber(image_dirs, image_roots),
                             )
except TomlAccessError:
    images_group = None
##-- end images
