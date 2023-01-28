##-- imports
from __future__ import annotations

import sys
import pathlib as pl
import shutil
import re
import fileinput

import doot
from doot.tasker import DootTasker, ActionsMixin

from doot.task_group import TaskGroup
##-- end imports
# https://pip.pypa.io/en/stable/cli/

# pip_version   = CmdTask("pip", "--version", verbosity=2, basename=f"{prefix}::version")

class IncrementVersion(DootTasker):
    """
    Increment semver of package.
    Defaults to inc patch version
    """

    def __init__(self, name="py::semver", locs=None):
        super().__init__(name, locs)
        self.initpy_ver_regex     = re.compile(r"^\s*__version__\s+=\s\"(\d+)\.(\d+)\.(\d+)\"")
        self.initpy_ver_format    = "__version__ = \"{}.{}.{}\""
        self.pyproject_ver_regex  = re.compile("^version\s+=\s+\"(\d+)\.(\d+)\.(\d+)\"")
        self.pyproject_ver_format = "version = \"{}.{}.{}\""
        assert(self.locs.root)
        assert(self.locs.src)

    def set_params(self):
        return [
            {"name" : "major", "long": "major", "type" : bool, "default" : False },
            {"name" : "minor", "short": "m", "type": bool, "default": False},
            {"name" : "force", "long": "force", "type": str, "default": None},
        ]


    def task_detail(self, task):
        task.update({
            "actions" : [self.increment_pyproject, self.set_initpy],
            "file_dep": [
                self.locs.root / "pyproject.toml",
                self.locs.src / "__init__.py"
            ],
            "verbosity" : 2,
        })
        return task

    def increment_pyproject(self):
        assert(not (self.args['major'] and self.args['minor']))
        new_ver = None
        for line in fileinput.input(files=[self.locs.root / "pyproject.toml"], inplace=True, backup=".backup"):
            matched = self.pyproject_ver_regex.match(line)
            if not matched or new_ver is not None:
                print(line, end="")
                continue

            new_ver = self.bump_version(*(int(x) for x in matched.groups()))
            print(self.pyproject_ver_format.format(*new_ver))

        if new_ver is None:
            raise Exception("Didn't find version in pyproject.toml")
        else:
            (self.locs.root / "pyproject.toml.backup").unlink()
            print(f"Bumped Version to: {new_ver}")

        return {"new_version" : new_ver}

    def set_initpy(self, dependencies, task):
        new_ver = task.values['new_version']
        for line in fileinput.input(files=[self.locs.src / "__init__.py"], inplace=True, backup=".backup"):
            matched = self.initpy_ver_regex.match(line)
            # Note the inverted condition compared to inc pyproject above:
            if not matched or new_ver is None:
                print(line, end="")
                continue

            print(self.initpy_ver_format.format(*new_ver))
            new_ver = None

        (self.locs.src/ "__init__.py.backup").unlink()

    def bump_version(self, major, minor, patch):
        match (self.args['major'], self.args['minor'], self.args['force']):
            case (_, _, str()):
                return tuple(int(x) for x in self.args['force'].split("."))
            case (True, False, _):
                return (major + 1, 0, 0)
            case (False, True, _):
                return (major, minor + 1, 0)
            case (False, False, _):
                return (major, minor, patch + 1)
            case _:
                raise Exception("this shouldn't happen")


class PipBuild(DootTasker, ActionsMixin):
    """
    Build a wheel of the package
    """

    def __init__(self, name="pip::build", locs=None):
        super().__init__(name, locs)
        assert(self.locs.wheel)
        assert(self.locs.temp)
        assert(self.locs.root)

    def task_detail(self, task):
        task['actions'].append(self.cmd(["pip", "wheel",
                                         "--no-input",
                                         "--wheel-dir", self.locs.wheel,
                                         "--use-pep517",
                                         "--src", self.locs.temp,
                                         self.locs.root]))
        return task

class PipInstall(DootTasker, ActionsMixin):
    """
    ([src]) install a package, using pip
    editable by default
    """

    def __init__(self, name=f"pip::install", locs=None):
        super().__init__(name, locs)
        assert(self.locs.root)


    def set_params(self):
        return [
            {"name" : "regular", "type": bool, "short": "r", "default": False},
            {"name" : "deps",   "type": bool, "short": "D", "default": False},
            {"name" : "dryrun", "type": bool, "long":"dry-run", "default": False},
            {"name" : "uninstall", "type": bool, "long":"uninstall", "default": False},
            {"name" : "upgrade", "type" : bool, "short" : "U", "default": False},
        ]

    def task_detail(self, task):
        task.update({
            "file_dep" : [self.locs.root / "requirements.txt"],
        })
        if self.args['uninstall']:
            task['actions'].append(self.cmd(["pip", "uninstall", "-y", self.locs.root]))
            return task

        if self.args['deps']:
            task['actions'].append(self.cmd(self.install_requirements))

        task['actions'].append(self.cmd(self.install_package))
        return task

    def install_requirements(self, dependencies):
        args = ["pip", "install", "--no-input", "--requirement", dependencies[0] ]
        if self.args['upgrade']:
            args.append('--upgrade')
        if self.args['dryrun']:
            args.append("--dry-run")

        return args

    def install_package(self):
        args = ["pip", "install", "--no-input"]
        if not self.args['regular']:
            args.append("--editable")
        if self.args['dryrun']:
            args.append("--dry-run")

        args.append(self.locs.root)
        return args



class PipReqs(DootTasker, ActionsMixin):
    """
    use pipreqs to make a concise requirements.txt
    """

    def __init__(self, name="pip::req", locs=None):
        super().__init__(name, locs)
        assert(self.locs.root)
        assert(self.locs.src)

    def is_current(self, task):
        return False

    def task_detail(self, task) -> dict:
        req_path = self.locs.root / "requirements.txt"
        pip_args = ["pipreqs", "--force", "--savepath", req_path, self.locs.src]
        task.update({
            "actions" : [ self.cmd(pip_args)
                        ],
            "targets" : [ req_path ],
            "clean"   : True,
            "verbosity" : 1,
        })
        return task

class VenvNew(DootTasker, ActionsMixin):
    """
    (-> temp ) create a new venv
    """
    def __init__(self, name="py::venv", locs=None):
        super().__init__(name, locs)
        assert(self.locs.temp)
        assert(self.locs.root)

    def set_params(self):
        return [
            { "name" : "name", "type": str, "short": "n", "default": "default"},
            { "name" : "delete", "type": bool, "long": "delete", "default": False},
        ]

    def task_detail(self, task):
        venv_path = self.locs.temp / "venv" / self.args['name']
        build_venv = [ self.cmd(["python", "-m", "venv", venv_path ]),
                       self.cmd([ venv_path / "bin" / "pip",
                                 "install",
                                 "-r", self.locs.root / "requirements.txt" ]),
                      ]

        is_delete = all([self.args['delete'],
                         venv_path.exists(),
                         (venv_path / "pyvenv.cfg").exists()])

        task.update({
            "actions" : [(self.rmdirs, [venv_path])] if is_delete else build_venv,
            "clean"   : [ (self.rmdirs, [venv_path]) ],
            "verbosity" : 1,
        })
        return task
