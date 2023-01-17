##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot.task_group import TaskGroup
from doot import globber
from doot.tasker import DootTasker

##-- end imports

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

class PDFMetaData(globber.EagerFileGlobber):
    """
    build metadata summaries of found pdfs
    """
    pass

class PDFBibtexMetaData(globber.EagerFileGlobber):
    """
    For found pdf's get bibtex data and add it into metadata
    """
    pass
