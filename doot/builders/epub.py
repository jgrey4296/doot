
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
import re
import shutil
from datetime import datetime
from importlib.resources import files
from os import environ
from string import Template
from uuid import uuid1
from doit.tools import Interactive

from bs4 import BeautifulSoup
from doit.action import CmdAction
from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.files.ziptask import ZipTask, zip_dir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# https://www.w3.org/publishing/epub3/epub-packages.html
# https://www.w3.org/publishing/epub3/epub-spec.html#sec-cmt-supported

epub_build_dir = build_dir / "epub"
working_dir    = pl.Path("docs") / "epub"
orig_dir       = pl.Path("orig") / "epub"

working_dirs = list(working_dir.iterdir()) if working_dir.exists() else []
epubs        = list(orig_dir.glob("**/*.epub")) if orig_dir.exists() else []
zips         = list(zip_dir.glob("*.zip")) if zip_dir.exists() else []

##-- dir check
check_working_epub = CheckDir(paths=[working_dir,
                                     epub_build_dir,
                                     orig_dir,
                                     ],
                              name="epub",
                              task_dep=["_checkdir::build"])
##-- end dir check

##-- epub templates
data_path      = files("doot.__templates")
MANIFEST_ENT_T = Template(data_path.joinpath("epub_manifest_entry").read_text())
MANIFEST_T     = Template(data_path.joinpath("epub_manifest").read_text())
SPINE_ENT_T    = Template(data_path.joinpath("epub_spine_entry").read_text())
NAV_T          = Template(data_path.joinpath("epub_nav").read_text())
NAV_ENT_T      = Template(data_path.joinpath("epub_nav_entry").read_text())
##-- end epub templates

ws = re.compile("\s+")

class EbookCompileTask:
    """
    convert directories to zips,
    then those zips to epubs
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in working_dirs:
            yield {
                "basename" : "epub::compile",
                "name"     : path.stem,
                "actions"  : [],
                "targets"  : [ ],
                "task_dep" : [ f"epub::manifest:{path.stem}",
                               f"_zip::epub:{path.stem}",
                               f"_epub::convert.zip:{path.stem}",
                              ],
            }



class EbookConvertTask:
    """
    *.zip -> *.epub
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build_epub(self, file_dep, targets):
        return

    def build(self):
        # TODO possibly only zips with the right contents
        for path in working_dirs:
            yield {
                "basename" : "_epub::convert.zip",
                "name"     : path.stem,
                "targets"  : [ epub_build_dir / path.with_suffix(".epub").name ],
                "file_dep" : [ zip_dir / path.with_suffix(".zip").name ],
                "actions"  : [ "ebook-convert {dependencies} {targets}" ],
                "task_dep" : ["_checkdir::epub",
                              f"_zip::epub:{path.stem}"
                              ],
                "clean"    : True,
            }



class EbookZipTask:
    """
    Zip working epub directories together
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in working_dirs:
            target = path.with_suffix(".zip").name
            glob = str(path) + "/**/*"
            task = ZipTask(target,
                           target_dir=zip_dir,
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
        # Map path -> uuid
        self.uuids = {}

    def init_uuids(self):
        self.uuids.clear()

    def get_uuid(self, path):
        if str(path) in self.uuids:
            return self.uuids[str(path)]
        else:
            p_uuid =  path.stem + "_" + hex(uuid1().time_low)
            self.uuids[str(path)] = p_uuid
            return p_uuid

    def backup(self, targets):
        for targ in [pl.Path(x) for x in targets]:
            if targ.exists():
                targ.rename(targ.with_suffix(".backup"))

    def get_type_string(self, path):
        match path.suffix:
            case ".html" | ".xhtml" | ".htm":
                type_s = "application/xhtml+xml"
            case ".js":
                type_s = "application/javascript"
            case ".css" | ".xpgt":
                type_s = "text/css"
            case ".gif":
                type_s = "image/gif"
            case ".jpg" | ".jpeg":
                type_s = "image/jpeg"
            case  ".png":
                type_s = "image/png"
            case ".svg":
                type_s = "image/svg+xml"
            case ".ttf":
                type_s = "font/ttf"
            case ".oft":
                type_s = "font/oft"
            case ".woff":
                type_s = "font/woff"
            case ".woff2":
                type_s = "font/woff2"
            case _:
                print("Unrecogized file type when constructing manifest: ", path)
                raise Exception()

        return type_s

    def get_title(self, path):
        soup = BeautifulSoup(path.read_text(), "html.parser")
        title = soup.h1
        if title is None:
            title = soup.title
        if title is None:
            title = "Default Title"

        return ws.sub(" ", title.text)

    def generate_nav(self, targets):
        nav     = pl.Path(targets[1])
        content = nav.parent
        entries = []
        for cont in content.glob("*"):
            if cont.suffix == ".backup":
                continue
            if cont.name == ".DS_Store":
                continue
            uuid  = self.get_uuid(cont)
            title = self.get_title(cont)
            entries.append(NAV_ENT_T.substitute(uuid=uuid,
                                                path=cont.relative_to(content),
                                                title=title).strip())

        nav.write_text(NAV_T.substitute(navs="\n".join(entries)))



    def generate_manifest(self, targets):
        """
        glob all files, construct the manifest from templates, write the file
        """
        manifest    = pl.Path(targets[0])
        date_str    = datetime.now().isoformat()
        author      = environ['USER']
        working_dir = manifest.parent
        manifest_entries = []
        spine_entries    = []
        guide_entries    = []
        for path in working_dir.glob("**/*"):
            if path.suffix in  [".backup", ".opf"]:
                continue
            if path.name == ".DS_Store":
                continue
            if path.is_dir():
                continue

            p_uuid = self.get_uuid(path)
            ext    = path.suffix
            try:
                type_s = self.get_type_string(path)
            except Exception:
                continue

            manifest_entries.append(MANIFEST_ENT_T.substitute(uuid=p_uuid,
                                                              path=path.relative_to(working_dir),
                                                              type=type_s).strip())

            # TODO ensure title -> nav -> rest
            if type_s == "application/xhtml+xml":
                spine_entries.append(SPINE_ENT_T.substitute(uuid=p_uuid).strip())


        expanded_template = MANIFEST_T.substitute(title=working_dir.stem,
                                                  author_sort=author,
                                                  author=author,
                                                  uuid=uuid1().hex,
                                                  date=date_str,
                                                  manifest="\n".join(manifest_entries),
                                                  spine="\n".join(spine_entries)
                                                  )
        manifest.write_text(expanded_template)



    def build(self):
        for path in working_dirs:
            yield {
                "basename" : "epub::manifest",
                "name"     : path.stem,
                "actions"  : [ self.init_uuids, self.backup, self.generate_nav, self.generate_manifest ],
                "targets"  : [ path / "content.opf", path / "content" / "nav.xhtml" ],
                "task_dep" : [ f"_epub::restruct:{path.stem}" ]
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
                "name"     : path.stem,
                "targets"  : [ working_dir / path.stem],
                "file_dep" : [ path ],
                "actions"  : [ "echo {dependencies}",
                                "echo {targets}",
                                "ebook-convert {dependencies} {targets}" ],
                "task_dep" : [ "_checkdir::epub" ],
            }


class EbookRestructureTask:
    """
    Reformat working epub dirs to the same structure
    *.x?htm?              -> content/
    *.css                 -> style/
    *.jpg|gif|png|svg     -> image/
    *.ttf|otf|woff|woff2  -> font/
    """

    def __init__(self):
        self.create_doit_tasks = self.build
        self.content_reg = re.compile(".+(x?html?|js)")
        self.style_reg   = re.compile(".+(css|xpgt)")
        self.img_reg     = re.compile(".+(jpg|gif|png|svg)")
        self.font_reg    = re.compile(".+(ttf|oft|woff2?)")

    def move_files(self, targets):
        root = pl.Path(targets[0]).parent
        for poss in root.glob("**/*"):
            if poss.is_dir():
                continue
            if poss.parent.name in ["content", "style", "image", "font"]:
                continue
            if poss.name == "titlepage.xhtml":
                poss.rename(root / poss.name)
                continue

            match poss.suffix:
                case x if self.content_reg.match(x):
                    poss.rename(root / "content" / poss.name)
                case x if self.style_reg.match(x):
                    poss.rename(root / "style" / poss.name)
                case x if self.img_reg.match(x):
                    poss.rename(root / "image" / poss.name)
                case x if self.font_reg.match(x):
                    poss.rename(root / "font" / poss.name)

    def build(self):
        # TODO retarget links
        for path in working_dirs:
            yield {
                "basename" : "_epub::restruct",
                "name" : path.stem,
                "actions" : [ "mkdir -p {targets}",
                              self.move_files,
                            ],
                "targets" : [ path / "content",
                              path / "style",
                              path / "image",
                              path / "font" ],
            }

class EbookNewTask:
    """
    Create a new stub structure for an ebook
    """
    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        return {
            "basename" : "epub::new",
            "actions" : [ "echo TODO {name}",
                f"mkdir -p {working_dir}/" + "{name}" ],
            "targets" : [],
            "params" : [ { "name" : "name",
                           "short" : "n",
                           "type" : str,
                           "default" : "default" } ],
        }
