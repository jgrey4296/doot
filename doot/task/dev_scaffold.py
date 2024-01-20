"""


"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
import shutil
from typing import ClassVar
from functools import partial

import doot
import doot.errors
from doot.structs import DootTaskSpec
from doot._abstract import Job_i
from doot.mixins.tasks.cleaning import CleanerMixin
from doot.task.base_job import DootJob
from doot.task.base_task import DootTask

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

make_missing = doot.config.on_fail(False).settings.general.location_check.make_missing()

@doot.check_protocol
class DevScaffold(DootJob):
    """ When Authoring a task, scaffold it with test data, run it, test the results, and cleanup


    """

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)

    def build(self, **kwargs):
        raise NotImplementedError("TODO")
