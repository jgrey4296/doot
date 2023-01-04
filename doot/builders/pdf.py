##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.task_group import TaskGroup
from doot.utils import globber
from doot.utils.tasker import DootTasker

##-- end imports


class SplitPDFTask(DootTasker):
    """
    For PDFs in directores, split them into separate pages
    """
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
