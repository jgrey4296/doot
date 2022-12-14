# -*- mode:doit; -*-
##-- imports
from __future__ import annotations
import pathlib as pl
##-- end imports

class TaskStub:
    """
    A Stub for easily building tasks
    """

    def __init__(self, *args, **kwargs):
        self.create_doit_tasks = self.build
        self.kwargs = kwargs
        self.default = {
            ## Required:
            # "actions"   : ((list, tuple), (None,)),
            ## Optional
            # "targets"   : ((list, tuple), ()),
            # "verbosity" : ((), (None, 0, 1, 2,)),

                               # "basename"  : (string_types, ()),
            # "title"     : ((Callable,), (None,)),
            # "name"      : (string_types, ()),
            # "meta"      : ((dict,), (None,))
            # "doc"       : (string_types, (None,)),
            # dependencies
            # "calc_dep"  : ((list, tuple), ()),
            # "task_dep"  : ((list, tuple), ()),
            # "file_dep"  : ((list, tuple), ()),
            # Pre/Post
            # "setup"     : ((list, tuple), ()),
            # "teardown"  : ((list, tuple), ()),
            # "clean"     : ((list, tuple), (True,)),

            # "getargs"   : ((dict,), ()),
            # "io"        : ((dict,), (None,)),
            # "params"    : ((list, tuple,), ()),
            # "pos_arg"   : (string_types, (None,)),
            # "uptodate"  : ((list, tuple), ()),
            # "watch"     : ((list, tuple), ()),
        }


    def uptodate(self):
        return True

    def action(self):
        pass

    def build(self) -> dict:
        task = self.default.copy()
        task.update(self.kwargs)

        return task

    def gen_toml(self):
        """ generate a toml skeleton for customizing this task? """
        pass
