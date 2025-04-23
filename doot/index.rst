.. ..  index.rst -*- mode: ReST -*-


.. _index:

================================
Doot: The Documentation
================================

.. contents:: Contents
   :local:

Doot is a TOML based Task Runner similar to `doit`_.
Probably use that instead of ``doot`` for the moment.


.. _intro:

Introduction
------------

Doot grew out of a desire for:

#. a task runner with less esoteric cantations than ``make``.
#. a CLI that would respond to ``--help`` at all stages of trying to remember what I was doing.
#. a `toml`_ based task specification format.
#. straightfoward use of ``Python`` functions when custom actions are needed.


Overview
--------

See the tasks available:

.. code:: bash

   doot list

Resulting in:

.. code:: bash

   ----------------------------------------------
   -------------------- Doot --------------------
   ----------------------------------------------
   Defined Task Generators by Group:
   *   docs::
            build               :: build sphinx project documentation                           :: <Source: /media/john/data/github/python/doot/.tasks/docs.toml>
            test                :: run sphinx doctest                                           :: <Source: /media/john/data/github/python/doot/.tasks/docs.toml>
   *   precommit::
            validate            :: Validate a commit message.                                   :: <Source: /media/john/data/github/_templates/doot/repo_chores/precommit.toml>
   *   test::
            pytest              :: run project tests                                            :: <Source: /media/john/data/github/_templates/doot/repo_chores/test.toml>
   *   version::
            major               ::                                                              :: <Source: /media/john/data/github/_templates/doot/repo_chores/version.toml>
            minor               ::                                                              :: <Source: /media/john/data/github/_templates/doot/repo_chores/version.toml>
            bump                ::                                                              :: <Source: /media/john/data/github/_templates/doot/repo_chores/version.toml>
            changelog           :: Generates a changelog using git cliff                        :: <Source: /media/john/data/github/_templates/doot/repo_chores/version.toml>
   *   requirements::
            pip                 :: Generate a requirements.txt                                  :: <Source: /media/john/data/github/_templates/doot/repo_chores/version.toml>

   Full Task Name: {group}::{task}

Then run one of the tasks:

.. code:: bash

   doot docs::build

Config Files
------------

There are two main config file types.

- :term:`doot.toml` for configuring doot, and

- :term:`task.toml` files for describing tasks and their relations.

doot.toml
#########

.. code:: toml

    # -*- mode:conf-toml; -*-

    [settings.general]
    loaders                  = { commands="default", task="default", parser="default"}
    location_check           = { make_missing = true }

    [settings.tasks]
    sources = [".tasks", "~/.config/.templates/doot/repo_chores"] # Files or directories where task specs can be loaded from, expanded according to [[locations]] keys
    code    = []                                       # Directories where task specific code can be imported from, expanded according to [[locations]] keys
    sleep   = { tasks=0.2, subtask=1, batch=1 }

    [settings.commands]
    # Settings for commands, like telling the 'run' command what backends to use
    run  = { tracker="default", runner="default", reporter= "default", report-line=[] }
    list = { hide=[] }

    [plugins]
    # Allows for defining aliases
    command        = { tasks="doot.cmds.list_cmd:ListCmd", pl="doot.cmds.plugins_cmd:PluginsCmd" }

    [logging]
    # Standard loggers. See LoggerSpec.
    stream  = { level="WARNING", filter=[],                 target="stdout", format="{levelname:<8} : {message}"  }
    file    = { level="DEBUG",   filter=["tomlguard"],      target="rotate", format="{levelname:<8} : {message:<20} :|: ({module}.{lineno}.{funcName})", filename_fmt="doot.log" }
    printer = { level="NOTSET",  colour=true,                target=["stdout", "rotate"], format="{message}", filename_fmt="doot_printed.log" }

    [logging.subprinters]
    default       = {level="WARNING"}
    shutdown      = {level="WARNING",    format="Shutdown: {message}", target="stdout"}
    cmd           = {level="INFO"}
    task          = {level="INFO" }
    header        = {level="INFO" }
    task_header   = {level="INFO"}

    [logging.extra]

    [[locations]]
    tasks        = ".tasks"
    temp         = {loc=".temp", cleanable=true}
    src          = {loc="doot", protected=true}
    logs         = "{temp}/logs"

Task Toml
#########

.. code:: toml

   [[tasks.simple]]
   name = "basic"
   actions = [
          {do="log", msg="This is a really simple task"},
   ]

   [[tasks.better]]
   name = "chained"
   depends_on = [ "simple::basic" ]
   actions = [
          {do="log", msg="This runs after simple::basic has run"},
   ]


.. _repo:

Repo and Issues
---------------

.. jgdir::



The repo for doot can be found `here <https://github.com/jgrey4296/doot>`_.

When you find a bug, bother me, unsurprisingly, on the `issue tracker <https://github.com/jgrey4296/doot/issues>`_.



.. toctree::
   :maxdepth: 3
   :hidden:

   __docs/getting_started
   __docs/cli
   __docs/examples/overview
   __docs/architecture/overview
   __docs/reference/reference
   __docs/misc/overview
   FAQ <__docs/faq>
   __docs/license
   __docs/glossary
   __docs/rst_tests

   genindex
   modindex
   API Reference <autoapi/doot/index>


.. .. Links
.. _doit: https://pydoit.org/contents.html
.. _toml: https://toml.io/en/
