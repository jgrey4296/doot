
#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doit.cmd_base import DoitCmdBase, check_tasks_exist, subtasks_iter
from collections import defaultdict

opt_listall = {
    'name': 'subtasks',
    'short': '',
    'long': 'all',
    'type': bool,
    'default': False,
    'help': "list include all sub-tasks from dodo file"
}

opt_list_quiet = {
    'name': 'quiet',
    'short': 'q',
    'long': 'quiet',
    'type': bool,
    'default': False,
    'help': 'print just task name (less verbose than default)'
}

opt_list_status = {
    'name': 'status',
    'short': 's',
    'long': 'status',
    'type': bool,
    'default': False,
    'help': 'print task status (R)un, (U)p-to-date, (I)gnored'
}

opt_list_private = {
    'name': 'private',
    'short': 'p',
    'long': 'private',
    'type': bool,
    'default': False,
    'help': "print private tasks (start with '_')"
}

opt_list_dependencies = {
    'name': 'list_deps',
    'short': '',
    'long': 'deps',
    'type': bool,
    'default': False,
    'help': ("print list of dependencies "
             "(file dependencies only)")
}

opt_template = {
    'name': 'template',
    'short': '',
    'long': 'template',
    'type': str,
    'default': None,
    'help': "display entries with template"
}

class ListCmd(DoitCmdBase):
    doc_purpose = "list tasks from dooter"
    doc_usage = "[TASK ...]"
    doc_description = None

    cmd_options = (opt_listall, opt_list_quiet, opt_list_status,
                   opt_list_private, opt_list_dependencies, opt_template)

    STATUS_MAP = {'ignore': 'I', 'up-to-date': 'U', 'run': 'R', 'error': 'E'}

    @classmethod
    def get_name(cls):
        return "list"

    def _print_task(self, template, task, status, list_deps, tasks):
        """print a single task"""
        line_data = {'name': task.name, 'doc': task.doc}
        # FIXME group task status is never up-to-date
        if status:
            # FIXME: 'ignore' handling is ugly
            if self.dep_manager.status_is_ignore(task):
                task_status = 'ignore'
            else:
                task_status = self.dep_manager.get_status(task, tasks).status
            line_data['status'] = self.STATUS_MAP[task_status]

        self.outstream.write(template.format(**line_data))

        # print dependencies
        if list_deps:
            for dep in task.file_dep:
                self.outstream.write(" -  %s\n" % dep)
            self.outstream.write("\n")

    def _execute(self, subtasks=False, quiet=True, status=False, private=False,
                 list_deps=False, template=None, pos_args=None):
        """List task generators"""
        filter_tasks = pos_args

        # grouped tasks:
        grouped_tasks = defaultdict(lambda: defaultdict(lambda: []))
        name_lens     = set()
        for task in self.task_list:
            names = task.name_parts()
            match names:
                case [x, *_] if bool(filter_tasks) and x.replace("_", "") not in filter_tasks:
                    continue
                case [x, *_] if x.startswith("_") and not private:
                    continue
                case [x, y, *_] if x.startswith("_"):
                    name_lens.add(len(task.name))
                    grouped_tasks[x[1:]][y].append(task)
                case [x, y, *_]:
                    name_lens.add(len(task.name))
                    grouped_tasks[names[0]][y].append(task)

        if quiet:
            self.outstream.write(f"Task Groups:\n")
            for group_name in sorted(grouped_tasks.keys()):
                self.outstream.write(f"\t{group_name}\n")
            return 0

        max_name_len = max(name_lens)
        # set template
        if template is None:
            template = '{name:<' + str(max_name_len + 3) + '}'
            if not quiet:
                template += '{doc}'

        for group_name in sorted(grouped_tasks.keys()):
            self.outstream.write(f"{group_name}:\n")
            reports = []
            for sub in sorted(grouped_tasks[group_name].keys()):
                reports += [x.report(template, list_deps) for x in grouped_tasks[group_name][sub]]

            self.outstream.write("\n".join(sorted(reports)))
            self.outstream.write("\n")

        return 0
