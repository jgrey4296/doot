##-- imports
from __future__ import annotations

import sys
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

    def __init__(self, name="py::semver", dirs=None):
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
            "verbosity" : 2,
        })
        return task

    def inc_ver(self, dependencies):
        assert(not (self.params['major'] and self.params['minor']))
        new_ver = None
        for line in fileinput.input(files=dependencies, inplace=True, backup=".backup"):
            matched = self.ver_regex.match(line)
            if not matched:
                print(line, end="")
                continue

            if new_ver is not None:
                raise Exception("this should't happen")

            new_ver = self.bump_version(*(int(x) for x in matched.groups()))
            print(self.ver_format.format(*new_ver))


        if new_ver is None:
            print("Didnt increment, adding")
            with open(dependencies[0], 'a') as f:
                print(self.ver_format.format(0,0,1), file=f)
        else:
            print(f"Bumped Version to: {new_ver}")

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
            {"name": "deps",   "type": bool, "short": "D", "default": False},
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

        if self.params['deps']:
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
    write out pip requirements to requirements.txt
    """

    def __init__(self, name="pip::req", dirs=None):
        super().__init__(name, dirs)

    def is_current(self, fpath):
        return True

    def task_detail(self, task) -> dict:
        pip_args = ["pip", "list", "--format=freeze"]

        task.update({
            "actions" : [ CmdAction(pip_args, shell=False, save_out="frozen"),
                          self.write_out,
                        ],
            "targets" : [ self.dirs.root / "requirements.txt" ],
            "clean"   : True,
            "verbosity" : 1,
        })
        return task

    def write_out(self, task, targets):
        with open(targets[0], 'w') as f:
            print(task.values['frozen'], file=f)


class VenvNew(DootTasker):
    """
    (-> temp ) create a new venv
    """
    def __init__(self, name="py::venv", dirs=None):
        super().__init__(name, dirs)

    def set_params(self):
        return [
            { "name" : "name", "type": str, "short": "n", "default": "default"},
            { "name" : "delete", "type": bool, "long": "delete", "default": False},
        ]

    def task_detail(self, task):
        venv_path = self.dirs.temp / self.params['name']
        build_venv = [ CmdAction(["python", "-m", "venv", venv_path ], shell=False),
                       CmdAction([ venv_path / "bin" / "pip", "install", "-r", self.dirs.root / "requirements.txt" ], shell=False)
                      ]
        def delete_venv():
            shutil.rmtree(venv_path)

        is_delete = all([self.params['delete'],
                         venv_path.exists(),
                         (venv_path / "pyvenv.cfg").exists()])

        task.update({
            "actions" : [delete_venv] if is_delete else build_venv,
            "clean"   : [delete_venv],
            "verbosity" : 1,
        })
        return task
