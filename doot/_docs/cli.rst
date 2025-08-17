.. -*- mode: ReST -*-

==========
CLI
==========

.. contents:: Contents
   :local:

Doot is designed with the expectation I will forget the call syntax for it.
With that in mind, the most important part of the CLI is the ``help`` command and ``--help`` parameter.


The general forms of calling doot are:

.. code:: bash

   doot --help
   doot [cmd] [args*] --help
   doot [task] [args*] --help

   doot [cmd] [args*]
   # Explicit run:
   doot run   [task] [args*] : [task] [args*]...
   # Implicit run:
   doot [task] [args*] : [task] [args*]...


----------------
The Help Command
----------------

A general access point for what you can do with ``doot``.

.. code:: bash

   doot help

.. code:: bash

    ----------------------------------------------
    -------------------- Doot --------------------
    ----------------------------------------------
    Doot Help Command: No Target Specified/Matched
    Available Command Targets:
    -- clean
    -- graph
    -- help
    -- list
    -- locs
    -- pl
    -- plugins
    -- run
    -- step
    -- stub
    -- tasks

    ------------------------------
    Call a command by doing 'doot [cmd] [args]'. Eg: doot list --help

------------------
The Help Parameter
------------------

Every command and Task can always take ``--help`` as parameter.
This will print the documentation for that command or task,
and fill in the values of the parameters specified so far.

.. code:: bash

   doot list --help

.. code:: bash

    ----------------------------------------------
    -------------------- Doot --------------------
    ----------------------------------------------

    Command: listcmd v0.1

    A simple command to list all loaded task heads.Set settings.commands.list.hide with a list of regexs to ignore

    Params:
    -all             (bool)    : List all loaded tasks, by group                         : Defaults to: True
    -locations       (bool)    : List all Loaded Locations                               : Defaults to: False
    -internal        (bool)    : Include internal tasks (ie: prefixed with an underscore) : Defaults to: False
    --dependencies=  (bool)    : List task dependencies                                  : Defaults to: False
    --dag=           (bool)    : Output a DOT compatible graph of tasks                  : Defaults to: False
    --groups=        (bool)    : List just the groups tasks fall into                    : Defaults to: False
    --by-source=     (bool)    : List all loaded tasks, by source file                   : Defaults to: False
    [pattern]        List tasks with a basic string pattern in the name                  : Defaults to: ""

    ---- Current Param Assignments:
    - help              : True

    ------------------------------
    Call a command by doing 'doot [cmd] [args]'. Eg: doot list --help
