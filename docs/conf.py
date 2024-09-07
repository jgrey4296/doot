# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
#
# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project   = 'doot'
copyright = '2024, jgrey'
author    = 'jgrey'
release   = '0.13.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.extlinks",

    ]

templates_path   = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

##-- alabaster
# https://alabaster.readthedocs.io/en/latest/index.html
html_theme       = "alabaster"
html_static_path = ["_static"]
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

# -- Imports
import doot
