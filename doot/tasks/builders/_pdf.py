##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot.core.task.task_group import TaskGroup
from doot import globber
from doot.tasker import DootTasker

##-- end imports

class TODOCombinePDFTask(globber.DootEagerGlobber):
    """
    Combine pdfs
    For pdfs in directories,
    concatenate them into one
    """
    pass

class TODOSamplePDFTask(globber.DootEagerGlobber):
    """
    sample pdfs
    For PDFs in each directory, get their leading n pages,
    and build a summary pdf
    """
    pass

class TODOPDFMetaData(globber.DootEagerGlobber):
    """
    pdf metadata
    build metadata summaries of found pdfs
    """
    pass

class TODOPDFBibtexMetaData(globber.DootEagerGlobber):
    """
    pdf bibtex metadata
    For found pdf's get bibtex data and add it into metadata
    """
    pass
