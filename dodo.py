# -*- mode:doit; -*-
"""

"""
# https://pydoit.org/
##-- imports
import pathlib as pl
from doit.action import CmdAction
from doit import create_after
from doit.tools import set_trace, Interactive, PythonInteractiveAction, LongRunning
from doit.task import clean_targets

import bkmkorg

import doot
##-- end imports

##-- config
datatoml    = doot.setup_py()
check_build = doot.check_build

DOIT_CONFIG = {
    "default_tasks" : [],
    "action_string_formatting" : "new",
    }

##-- end config

##-- post-config doot imports
from doot.files.clean_cache import CleanCacheAction, py_cache_globs
from doot.files.listall import task_listall

def task_process_threads():
    """
    get all orgs, move them to appropriate subdir,
    then get all those orgs and split them
    then convert to html
    """
    def glob_orgs(root):
        for org in pl.Path(root).glob("*/*.org"):
            # move them
            # move their files
            pass

    def split_orgs(root):
        for org in pl.Path(root).glob("**/*.org"):
            pass

    return {
        "actions" : [glob_orgs_down, split_orgs ],
        "paramms" : [
            {"name"    : "root",
             "type"    : str,
             "default" : "/Volumes/documents/twitterthreads/"
            }
        ]
    }

def task_tesseract():
    """
    run tesseract on a directory
    """
    cmd = "find {dir} -type f | tesseract stdin ocr_result -l eng pdf"
    return {
        "actions" : [cmd],
        "params" : [
            { "name" : "dir",
             "short" : "d"
             "type" : str,
             "default" : ".",
             }
            ]
    }

def task_hash():
    """
    hash files by directory
    """

    return {
        "actions" : [ "find {dir} -type f -print0 | xargs -0 md5 >> {targets}"],
        "targets" : [ "all_md5s" ],
        "params" : [
            { "name" : "dir",
             "short" : "d"
             "type" : str,
             "default" : ".",
             }
            ]
    }
