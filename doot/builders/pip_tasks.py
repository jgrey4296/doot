##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction
import re
import fileinput

import doot
from doot.utils.cmdtask import CmdTask

from doot.utils.task_group import TaskGroup
##-- end imports
# https://pip.pypa.io/en/stable/cli/
# TODO add increment version tasks, plus update __init__.py
from doot.utils.tasker import DootTasker

prefix = doot.config.or_get("pip").tool.doot.pip.prefix()

# pip_version   = CmdTask("pip", "--version", verbosity=2, basename=f"{prefix}::version")

class IncrementVersion(DootTasker):
    """
    Increment semver of package.
    Defaults to inc patch version
    """

    def __init__(self, name="py::version.up", dirs=None):
        super().__init__(name, dirs)
        self.ver_regex = re.compile(r"^\s*__version__\s+=\s\"(\d+)\.(\d+)\.(\d+)\"")
        self.ver_format = "__version__ = \"{}.{}.{}\""

    def set_params(self):
        return [
            {"name" : "major", "long": "major", "type" : bool, "default" : False },
            {"name": "minor", "short": "m", "type": bool, "default": False},
        ]

    def task_detail(self, task):
        task.update({
            "actions" : [self.inc_ver],
            "file_dep": [self.dirs.src / "__init__.py"],
        })
        return task

    def inc_ver(self, dependencies):
        assert(not (self.params['major'] and self.params['minor']))
        incremented = False
        for line in fileinput.input(files=dependencies, inplace=True):
            matched = self.ver_regex.match(line)
            if incremented:
                raise Exception("this should't happen")
            if not matched:
                print(line, end="")
                continue

            new_ver = self.bump_version(*(int(x) for x in matched.groups()))
            print(self.ver_format.format(*new_ver))
            incremented = True

        if not incremented:
            with open(dependencies[0], 'a') as f:
                print(self.ver_format.format(0,0,1))

    def bump_version(self, major, minor, patch):
        match (self.params['major'], self.params['minor']):
            case (True, False):
                return (major + 1, 0, 0)
            case (False, True):
                return (major, minor + 1, 0)
            case (False, False):
                return (major, minor, patch + 1)
            case _:
                raise Exception("this shouldn't happen")


class PyBuild(DootTasker):

    def __init__(self, name="pip::build", dirs=None):
        super().__init__(name, dirs)

    def set_params(self):
        return []

    def task_detail(self, task):
        task.update({})

        task['actions'].append(CmdAction(["pip", "wheel", "--no-input", "--wheel-dir", self.dirs.extra['wheel'], "--use-pep517", "--src", dirs.temp, self.dirs.root], shell=False))
        return task

class PyInstall(DootTasker):
    """
    ([src]) install a package, using pip
    editable by default
    """

    def __init__(self, name=f"pip::install", dirs=None):
        super().__init__(name, dirs)

    def set_params(self):
        return [
            {"name": "regular", "type": bool, "short": "r", "default": False},
            {"name": "nodep",   "type": bool, "short": "D", "default": False},
            {"name" : "dryrun", "type": bool, "long":"dry-run", "default": False},
            {"name" : "uninstall", "type": bool, "long":"uninstall", "default": False},
            {"name": "upgrade", "type" : bool, "short" : "U", "default": False},
        ]

    def task_detail(self, task):
        task.update({
            "file_dep" : [self.dirs.root / "requirements.txt"],
        })
        if self.params['uninstall']:
            task['actions'].append(CmdAction(["pip", "uninstall", "-y", self.dirs.root], shell=False))
            return task

        if not self.params['nodep']:
            task['actions'].append(CmdAction(self.install_requirements, shell=False))

        task['actions'].append(CmdAction(self.install_package, shell=False))
        return task

    def install_requirements(self, dependencies):
        args = ["pip", "install", "--no-input", "--requirement", dependencies[0] ]
        if self.params['upgrade']:
            args.append('--upgrade')
        if self.params['dryrun']:
            args.append("--dry-run")

        return args

    def install_package(self):
        args = ["pip", "install", "--no-input"]
        if not self.params['regular']:
            args.append("--editable")
        if self.params['dryrun']:
            args.append("--dry-run")

        args.append(self.dirs.root)
        return args



class PipReqs(DootTasker):
    """
    write out pip requirements
    """

    def __init__(self, name="pip::req", dirs=None):
        super().__init__(name, dirs)

    def task_detail(self, task) -> dict:
        args1 = ["pip", "freeze", "--all", "--exclude-editable",
                "-r", "requirements.txt"]
        args2 = ["pip", "list", "--format=freeze"]

        task.update({
            'basename': f"{prefix}::requirements",
            "actions" : [ CmdAction(args1, shell=False, save_out="first"),
                          CmdAction(args2, shell=False, save_out="second"),
                          self.write_out,
                        ],
            "targets" : [ self.dirs.root / "requirements.txt" ],
            "clean"   : True,
            "doc" : ":: generate requirements.txt ",
        })
        return task

    def write_out(self, task, targets):
        with open(targets[0], 'w') as f:
            print(task.values['first'], file=f)
            print(task.values['second'], file=f)


class VenvNew(DootTasker):
    """
    create a new venv
    """
    pass
