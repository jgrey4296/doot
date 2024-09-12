#!/usr/bin/env python3
# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use pl.Path.resolve to make it absolute, like shown here.
#
import os
import sys
import pathlib as pl
sys.path.insert(0, pl.Path('../').resolve())

# (Relative to this file):
templates_path   = ['_templates']
html_static_path = ['_static']

# Relative to static dir, or fully qualified urls
html_css_files = ["custom.css"]
html_js_files  = []
# html_style = "custom.css"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['**/flycheck_*.py', "**/__tests/*"]

# -- Project information -----------------------------------------------------

project   = 'doot'
copyright = '2024, jgrey'
author    = 'jgrey'
release   = '0.13.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.extlinks',
    'sphinx_rtd_theme'
    'myst_parser',
    ]

# -- Options for HTML output -------------------------------------------------
html_theme       = "sphinx_rtd_theme"

##-- alabaster options
# https://alabaster.readthedocs.io/en/latest/index.html
extlinks         = {}
html_sidebars    = {
    "**": [
        "about.html",
        "searchfield.html",
        "navigation.html",
        "relations.html",
    ]
}

html_theme_options = {
    "description": "Doot, a simple TOML based task runner",
    "github_user": "jgrey4296",
    "github_repo": "doot",
    "fixed_sidebar": True,
    "github_banner": False,
    "show_related" : True,
}

##-- end alabaster

##-- rtd options
# https://sphinx-rtd-theme.readthedocs.io/en/stable/configuring.html

html_theme_options = {
    'logo_only'                   : False,
    'display_version'             : True,
    'prev_next_buttons_location'  : 'bottom',
    'style_external_links'        : False,
    'vcs_pageview_mode'           : '',
    'style_nav_header_background' : 'grey',
    # TOC options:
    'collapse_navigation'         : True,
    'sticky_navigation'           : True,
    'navigation_depth'            : 4,
    'includehidden'               : True,
    'titles_only'                 : False

}

##-- end rtd options

# Imports --------------------------------------------------
import doot
doot._test_setup()
