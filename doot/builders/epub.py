##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doit.action import CmdAction
from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.files.ziptask import ZipTask, zip_dir

##-- end imports

epub_working_dir = pl.Path("docs") / "epub"
epub_build_dir   = build_dir / "epub"
epub_zip_dir     = zip_dir

working_dirs = [x.parent for x in epub_working_dir.glob("**/titlepage.xhtml")]
epubs        = list(pl.Path(".").glob("**/*.epub"))
zips         = list(epub_zip_dir.global("*.zip"))
##-- dir check
check_working_epub = CheckDir(paths=[epub_working_dir], name="epub.working")
check_build_epub   = CheckDir(paths=[epub_build_dir], name="epub.build", task_dep=["_checkdir::build"])
check_zip_dir      = CheckDir(paths=[epub_zip_dir],   name="epub.zip", task_dep=["_checkdir::build"])
##-- end dir check

class EbookCompileTask:
    """
    convert directories to zips,
    then those zips to epubs
    """

    def __init__(self, ebook):
        self.create_doit_tasks = self.build

    def build(self):
        for path in working_dirs:
            yield {
                "basename" : "epub::compile"
                "name"     : path.name,
                "actions"  : [],
                "targets"  : [],
                "task_dep" : [ f"_epub::manifest:{path.name}",
                               f"_zip::epub:{path.name}",
                               f"_epub::convert.zip:{path.name}",
                              ],
            }



class EbookConvertTask:
    """
    *.zip -> *.epub
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build_epub(self, file_dep, targets):
        return "ebook-convert {file_dep} {targets}"

    def build(self):
        # TODO possibly only zips with the right contents
        for path in
            yield {
                "basename" : "_epub::convert.zip",
                "name"     : path.name,
                "targets"  : [ (epub_build_dir / path.name).with_suffix(".zip") ],
                "file_dep" : [ path ],
                "actions"  : [ self.build_epubs ],
                "task_dep" : ["_checkdir::epub.zip",
                              "_checkdir::epub.build",
                              "_zip::epub:{path.name}"
                              ],
            }



class EbookZipTask:


    """
    Zip working epub directories together
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in working_dirs:
            target = path.name.with_suffix(".zip")
            glob = str(path) + "/**/*"
            task = ZipTask(target,
                           target_dir=epub_zip_dir,
                           globs=[glob],
                           base="_zip::epub",
                           name=path.name,
                           )

            yield task.build()


class EbookManifestTask:
    """
    Generate the manifest for an epub directory
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def generate_manifest(self, targets):
        pass

    def generate_navmap(self, targets):
        pass

    def build(self):
        for path in working_dirs:
            yield {
                "basename" : "_epub::manifest",
                "name"     : path.name,
                "actions"  : [ self.generate_manifest, self.generate_navmap ],
                "targets"  : [ path / "content.opf", path / "toc.nxc"],
            }


class EbookSplitTask:
    """
    split any epubs found in the project
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in epubs:
            yield {
                "basename" : "epub::split",
                "name"     : path.name,
                "targets"  : [ epub_working_dir / path.name ],
                "file_dep" : [ path ],
                "actions"  : [ "ebook-convert {file_dep} {targets}" ],
                "task_dep" : ["_checkdir::epub.working"],
            }
