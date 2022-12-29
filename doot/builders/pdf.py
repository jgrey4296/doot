##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup
from doot.utils import globber

##-- end imports


class SplitPDFTask:
    """
    For PDFs in directores, split them into separate pages
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        pass


class CombinePDFTask(globber.DirGlobber):
    """
    For pdfs in directories,
    concatenate them into one
    """
    pass



class SamplePDFTask(globber.DirGlobber):
    """
    For PDFs in each directory, get their leading n pages,
    and build a summary pdf
    """
    pass

class PDFMetaData(globber.FileGlobberMulti):
    """
    build metadata summaries of found pdfs
    """
    pass

class PDFBibtexMetaData(globber.FileGlobberMulti):
    """
    For found pdf's get bibtex data and add it into metadata
    """
    pass
