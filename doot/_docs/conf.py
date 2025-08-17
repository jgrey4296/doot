#!/usr/bin/env python3
"""
Configuration file for the Sphinx documentation builder.
https://www.sphinx-doc.org/en/master/usage/configuration.html

"""
# ruff: noqa: TC003, A001, DTZ005, ERA001, PLR2044, ARG001, ANN001, ANN201, F401
# Imports --------------------------------
from __future__ import annotations
import os
import sys
import pathlib as pl
import datetime
import tomllib
from collections.abc import Sequence, Callable
from typing import Literal
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx.locale import __
from sphinx.util.docutils import SphinxDirective
# Types ----------------------------------
exclude_patterns       : list[str]
extensions             : list[str]
highlight_options      : dict
html_domain_indices    : bool|Sequence[str]
html_additional_pages  : dict
html_search_options    : dict
html_js_files          : list
html_sidebars          : dict
html_static_path       : list
html_theme_path        : list
html_extra_path        : list
html_style             : list[str] | str
include_patterns       : list[str]
needs_extensions       : dict[str, str]
nitpick_ignore         : set[tuple[str, str]]
nitpick_ignore_regex   : set[tuple[str, str]]
source_suffix          : dict[str, str]
templates_path         : list
napoleon_type_aliases  : dict
# ##--|

# ##-- a: Project information --------------------
project    = 'Doot'
author     = 'John Grey'
copyright  = '{}, {}'.format(datetime.datetime.now().strftime("%Y"), author)
language   = "en"
release    = tomllib.loads((pl.Path.cwd() / "../../pyproject.toml").read_text())['project']['version']

"""https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration"""
root_doc                       = "index"
primary_domain  = "py"
default_role                   = None

root_doc                       = "index"
suppress_warnings              = ["autoapi", "docutils"]
maximum_signature_line_length  = 50
toc_object_entries            = True
add_function_parentheses       = True
show_warning_types             = True
nitpick_ignore                 = set()
nitpick_ignore_regex           = set()
# Pygments: https://pygments.org/docs/lexers
highlight_options              = {}
pygments_style                 = "sphinx"

"""List of patterns, relative to source directory, that match files and
directories to incldue/ignore when looking for source files.
These also affects html_static_path and html_extra_path.
"""
include_patterns = [
    "**",
]
exclude_patterns = [
    "**/flycheck_*.py",
    "**/__tests/*",
    "_docs/_templates/*",
    "README.md",
]
source_suffix = {
    ".rst"  : "restructuredtext",
    ".txt"  : "restructuredtext",
    # ".md"   : "markdown",
}

# ##-- b: Extensions -----------------------------
extensions      = [
"myst_parser",
"sphinx_rtd_theme",
# Shorten external links: https://www.sphinx-doc.org/en/master/usage/extensions/extlinks.html
"sphinx.ext.extlinks",
# Runs docstring code? https://www.sphinx-doc.org/en/master/usage/extensions/doctest.html
"sphinx.ext.doctest",
# Alternative docstring formats: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
"sphinx.ext.napoleon",
# imagemagick conversion: https://www.sphinx-doc.org/en/master/usage/extensions/imgconverter.html
"sphinx.ext.imgconverter",
# Graph diagrams: https://www.sphinx-doc.org/en/master/usage/extensions/graphviz.html
"sphinx.ext.graphviz",
# Generates API by parsing, not importing: https://sphinx-autoapi.readthedocs.io/en/latest/
"autoapi.extension",
# For autapi's show-inheritance-diagram: https://www.sphinx-doc.org/en/master/usage/extensions/inheritance.html#module-sphinx.ext.inheritance_diagram
"sphinx.ext.inheritance_diagram",
# Link to other projects: https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
"sphinx.ext.intersphinx",
# Refernce sections by title: https://www.sphinx-doc.org/en/master/usage/extensions/autosectionlabel.html
# "sphinx.ext.autosectionlabel",
#--
# Extensions which IMPORT CODE:
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
# "sphinx.ext.autodoc",
# Generate autodocs: https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html
# "sphinx.ext.autosummary",
# Build test coverage reports: https://www.sphinx-doc.org/en/master/usage/extensions/coverage.html
# "sphinx.ext.coverage",
# Link descriptions to code: https://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html
"sphinx.ext.viewcode",

]
needs_extensions  = {
    # ExtName : Version
}

# -- Path setup ----------------------------------
# local_mod = str(pl.Path.cwd().parent)
local_mod = str(pl.Path("../../").resolve())
sys.path.insert(0, local_mod)

# ##-- Templates ---------------------------------
# Fully qualified class of TemplateBridge
# template_bridge = ""
# Relative to this file:
templates_path    = ["_templates"]

# ##-- HTML --------------------------------------
"""By default, the read the docs theme.
https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
"""
html_use_index      = True
html_split_index              = False
html_permalinks               = True
html_copy_source              = True
html_show_sourcelink          = True
html_show_search_summary      = False
html_codeblock_linenos_style  = "inline"  # or "table"
# --
html_theme_options            = {}
html_sidebars                 = {} # Maps doc names -> templates
html_additional_pages         = {} # Maps doc names -> templates
html_context                  = {}
html_search_options           = {}
# (Relative to this file):
# html_theme_path   = []
html_static_path  = ["_static"]
html_extra_path   = []  # for things like robots.txt
# html_style        = []
# html_logo       = ""
# html_favicon    = ""
# Relative to static dir, or fully qualified urls
html_css_files       = ["custom.css"]
html_js_files        = ["custom.js"]
# Generate additional domain specific indices
html_domain_indices  = ["py-modindex"]
#
html_additional_pages.update({})
html_context.update({
    "collapse_index_py": True,
})

# ##-- HTML Theme: ReadTheDocs -------------------
"""https://sphinx-rtd-theme.readthedocs.io/en/stable/configuring.html"""
html_theme = "sphinx_rtd_theme"
#
html_theme_options.update({
    "logo_only"                   : False,
    "prev_next_buttons_location"  : "bottom",
    "style_external_links"        : False,
    "vcs_pageview_mode"           : "",
    "style_nav_header_background" : "grey",
    # "version_selector"             : True,
    # TOC options:
    "collapse_navigation"         : True,
    "sticky_navigation"           : True,
    "navigation_depth"            : 4,
    "includehidden"               : True,
    "titles_only"                 : False,
})

# ##-- RST Options -------------------------------
# rst_prolog = ""
# rst_epilog = ""

# ##-- Python Domain -----------------------------
python_maximum_signature_line_length  : int | None
#--
add_module_names                                = True
python_display_short_literal_types              = False
python_trailing_comma_in_multi_line_signatures  = True
python_user_unqualified_type_names              = False
trim_doctest_flags                              = True
# Remove prefixes for indexiing
modindex_common_prefix                = ["doot."]
python_maximum_signature_line_length  = None

# ##-- c: Extension Options ----------------------
# ##-- Autodoc -----------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
#-- Events
# autodoc-process-docstring
# autodoc-before-process-signature
# autodoc-process-signature
# autodoc-process-bases
# autodoc-skip-member
#--
autodoc_typehints           = "both"
autodoc_typehints_format    = "short"
autodoc_inherit_docstrings  = False

# ##-- Autoapi -----------------------------------
autoapi_prepare_jinja_env : Callable[[jinja2.Environment], None] | None
#-- Events
# 'autoapi-skip-member' : Callable[[app, what, name, obj, skip, options], bool|None]
#--
# https://sphinx-autoapi.readthedocs.io/en/latest/reference/config.html
# For keeping generated files:
autoapi_keep_files                       = True
autoapi_generate_api_docs = True
autoapi_python_user_implicit_namespaces  = False
# If false, manual toctree entry (eg: _docs/autoapi/doot/index) needs to be added:
autoapi_add_toctree_entry = False
autoapi_type              = "python"
# Whether to use class docstring ro __init__ docstring.
autoapi_python_class_content  = "class" # 'both' | 'init'
autoapi_own_page_level        = "module" # class | function | method | attribute
# Relative to source dir:
autoapi_template_dir      = "_docs/_templates/autoapi"
# Directory to generate to. relative to source directory.
autoapi_root              = "_docs/_autoapi"
autoapi_dirs              = ["."]
autoapi_file_patterns     = ["*.py", "*.pyi"]
autoapi_ignore            = [*exclude_patterns, "*_docs/conf.py"]
autoapi_member_order      = "bysource" # 'alphabetical' | 'bysource' | 'groupwise'
autoapi_options           = [
    # "imported-members",
    # "inherited-members",
    # "show-inheritance-diagram",
    "members",
    "undoc-members",
    "private-members",
    "special_members",
    "show-inheritance",
    "show-module-summary",
]
# Warnings
suppress_warnings += [
    # "autoapi",
    # "autoapi.python_import_resolution",
    # "autoapi.not_readable",
    # "autoapi.toc_reference",
    # "autoapi.nothing_rendered",
]

# ##-- Extlinks ----------------------------------
extlinks : dict[str, tuple[str, str]]
#--
extlinks_detect_hardcoded_links  = False
# create roles to simplify urls. format: {rolename: [linkpattern, caption]}
extlinks = {
    # Add ':issue:' role:
    "issue": ("https://github.com/jgrey4296/doot/issues/%s", "issue %s"),
}

# ##-- Intersphinx -------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
type InterTuple      = tuple[str, tuple[str, str | None] | None]
intersphinx_mapping      : dict[str, InterTuple]
intersphinx_cache_limit  : int
intersphinx_timeout      : int | float | None
#--
# Map to other documentation using :external:
intersphinx_mapping = {
    # eg: :external+python:ref:`comparisons`
    "python" : ("https://docs.python.org/3", None),

}
intersphinx_cache_limit  = 5 # days
intersphinx_timeout      = None

# ##-- Graphviz ----------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/graphviz.html
#--
# Command name to invoke dot:
graphviz_dot            =  "dot"
graphviz_dot_args       = ()
graphviz_output_format  = "svg"  # or "dot"

# ##-- imgconvert --------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/imgconverter.html
#--
# Path to conversion command:
image_converter       = "convert"
image_converter_args  = ()

# ##-- Viewcode ----------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html
#-- Events:
# viewcode-find-source(app, modname) -> tuple[str, dict]
# viewcode-follow-imported(app, modname, attribute)
#--
# Blocks 'viewcode-follow-imported' event:
viewcode_follow_imported_members  = False
viewcode_enable_epub              = False
viewcode_line_numbers             = True

def no_import_viewcode_find_source(app, modname) -> tuple[str, dict]:
    """Event handler to find sourcecode *without* importing it"""
    type SourceCode  = str
    type Definition  = str
    type LineNum     = int
    type Tag         = Literal["class"] | Literal["def"] | Literal["other"]
    type TagsDict    = dict[str, dict[Definition, tuple[Tag, LineNum, LineNum]]]
    tags    : TagsDict
    source  : SourceCode
    #--
    source  = ""
    tags    = {}

    # Find the file
    # Parse the File
    # Map to dict
    # return
    return (source, tags)

# ##-- Autosection Labels ------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autosectionlabel.html
#--
# If true, ref is :ref:`docname:title`, else :ref:`title`
autosectionlabel_prefix_document  : bool        = False
autosectionlabel_maxdepth         : int | None  = None

# ##-- Napoleon Docstrings -----------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
napoleon_google_docstring               = True
napoleon_numpy_docstring                = True
napoleon_include_init_with_doc          = False
napoleon_include_private_with_doc       = False
napoleon_include_special_with_doc       = True
napoleon_use_admonition_for_examples    = False
napoleon_use_admonition_for_notes       = False
napoleon_use_admonition_for_references  = False
napoleon_use_ivar                       = False
napoleon_use_param                      = True
napoleon_use_rtype                      = True
napoleon_preprocess_types               = False
napoleon_attr_annotations               = True
napoleon_type_aliases                   = {}

# ##-- d: Sphinx App Customisation ---------------
# ##-- Jinja
try:
    import jinja2
except ImportError:
    jinja2 = None # type: ignore[assignment]
else:
    def filter_contains(val:list|str, *needles:str) -> bool:
        match val:
            case str():
                return any(x in val for x in needles)
            case list():
                joined = " ".join(val)
                return any(x in joined for x in needles)
            case _:
                return False
    
    def autoapi_prepare_jinja_env(jinja_env: jinja2.Environment) -> None:
        jinja_env.add_extension("jinja2.ext.debug")
        jinja_env.tests['contains'] = filter_contains
    
    def add_jinja_ext(app):
        app.builder.templates.environment.add_extension("jinja2.ext.debug")
    
# ##-- Sphinx and Jinja configuration ------------

def setup(app):
    if jinja2 is not None:
        app.events.connect("builder-inited", add_jinja_ext, 1)
