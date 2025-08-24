.. -*- mode: ReST -*-

.. _getting_started:

================
Getting Started
================

.. contents:: Contents
   :local:

------------
Installation
------------

Surprising no one:

.. code-block:: bash

   pip install doot
   # or
   uv add doot

   

-----------------
Starting Concepts
-----------------

1. Files.

   The **doot.toml** file marks the root of a doot project. The **.tasks** directory contain tasks sepcifications, in TOML files. See :ref:`DootFileRef` and :ref:`TaskFileRef`.

2. Commands.

   Calling **doot** from the command line. See :ref:`runcmd`, :ref:`listcmd`, :ref:`stubcmd`.

3. Tasks and Actions.

   Specified in task toml files, these declaratively describe what you want to do. See :ref:`tasksRef`.

4. Names

   To refer to tasks, either from the command line, or from other tasks, they need a name. This takes the form of **group::name**. See :ref:`namesRef`.

-------------
The Doot File
-------------

To start using doot, run ``doot stub --config`` to generate a config file in the project root.
This allows you to customize plugins, locations, logging etc.

.. code:: toml
          
   
   # -*- mode:toml; -*-
   # Config File for doot (http://github.com/jgrey4296/doot)
   
   [startup]
   # The version this config file works with:
   doot_version         = "1.1"
   loaders              = { commands="default", task="default", parser="default" }
   sources              = { tasks=[".tasks"], code=[] }
   skip_default_plugins = false
   skip_plugin_search   = false
   # Implicit Cmds. prepended to the raw cli args if no cmd is parsed
   empty_cmd            = ["list"]
   implicit_task_cmd    = ["run"]
   # constants_file     = ""
   # aliases_file       = ""
   
   [shutdown]
   notify           = { exit="Dooted" } # success_msg="", fail_msg=""
   defaulted_values = { write=false, path=".defaulted_values.toml" }
   # exit_on_load_failures = true
   
   [settings.commands]
   # Set command specific values, and aliases
   # if an entry has an aliases entry, the cmd is called with the given args
   [settings.commands.run]
   tracker         = "default"
   runner          = "default"
   reporter        = "default"
   location_check  = { active=true, make_missing=false, strict=true }
   sleep           = { task=0.2, subtask=1, batch=1 }
   max_steps       = 100_000
   # stepper         = { break_on="job" }
   
   [logging]
   # Setup output 'stream', 'file' and 'printer' logging.
   # See jgdv.logging for details.
   # Or call 'doot list --loggers'
   # Loggers can be in line format:
   # stream  = { level="WARN", filter=[],  target="stdout",   format="{levelname:<8} : {message}"  }
   # And disabled quickly using:
   # stream = false
   # Or as sections:
   
   [logging.stream]
   disabled  = false
   level     = "user"
   filter    = []
   # allow     = []
   target    = ["stdout"]
   format    = "{levelname:<8} : {message}"
   
   [logging.file]
   disabled      = true
   level         = "trace"
   filter        = ["jgdv"]
   target        = ["rotate"]
   format        = "{levelname:<8} : {message:<20} :|: ({module}.{lineno}.{funcName})"
   filename_fmt  = "doot.log"
   
   [logging.printer]
   disabled      = false
   level         = "NOTSET"
   colour        = true
   target        = ["stdout"]
   format        = "{message}"
   filename_fmt  = "doot_printed.log"
   
   [logging.extra]
   # Control specific loggers by their path.
   
   [[locations]]
   # Locations as structured strings. See jgdv.structs.locator
   src     = "src"
   temp    = "clean::.temp"
   logs    = "{temp}/logs"
   build   = "{temp}/build"
   docs    = "docs"
   data    = "data"
   
   [[global]]
   # Global State shared between tasks


---------------
Your First Task
---------------

.. code:: bash

   doot stub basic::task


.. code:: toml

   [[tasks.basic]]
   name             = "task"
   version          = "0.1"       # <str>                #
   doot_version     = "1.1.1"     # <str>
   doc              = []          # <list>               #
   ctor             = "task"      # <str>                #
   depends_on       = []          # <list[ActionSpec | RelationSpec]> #
   required_for     = []          # <list[RelationSpec]>              #
   setup            = []          # <list[ActionSpec | RelationSpec]> #
   cleanup          = []          # <list[ActionSpec | RelationSpec]> #
   actions          = []          # <list[ActionSpec | RelationSpec]> #

   
Actions in Groups
--------------

Currently ``basic::task`` doesn't actually do anything.
Actions can be added in the ``actions`` list of task. eg: 

.. code:: toml

   actions = [
      {do="log", msg="This is an example Action"},
   ]
          

It doesn't do anything special, but by calling ``doot basic::task`` (or more fully, ``doot run basic::task``),
the task will be constructed and run, printing out the message.

Available actions can be listed with ``doot list -actions``. 
The default action groups, run in order, are::

1. depends_on.
2. setup.
3. actions
4. cleanup
   

Adding CLI Params
-----------------

Tasks can take CLI Params. The ``doot stub -cli`` command provides the form as a reminder.

.. code:: toml

   [[tasks.basic]]
   name = "cli.example"
   docs = ["Call this as: doot basic::cli.example -gimme blah"]
   cli = [{ name="gimme", type="str", prefix="-", default="NOTHING" }]
   actions = [
          {do="log", msg="{gimme} was passed in at the CLI"},
   ]

----------------------
Chaining a Second Task
----------------------

Tasks can be chained together, both as dependencies, and as successor tasks.
For now, lets focus just on dependencies.

.. code:: toml

   [[tasks.basic]]
   name = "dependency.example"
   docs = ["basic::cli.example will run first, then this task"]
   depends_on = ["basic::cli.example"]
   actions = [
      {do="log", msg="This will come second"},
   ]


Passing Information between the Tasks
-------------------------------------

Tasks can pass information between each other using two mechanisms:

1. Injection into state as part of the dependency specification.
2. Using ``Postboxes``.


.. code:: toml

   [[tasks.basic]]
   name = "message.passing"
   actions = []

Cleaning Up
-----------

Tasks can specify actions to perform after they have completed.
They will run as separate tasks of the form ``TASKNAME.$cleanup``.

.. code:: toml

   [[tasks.basic]]
   name = "showing.cleanup"
   actions = []
   cleanup = []

----------------------------
Handling Files And Locations
----------------------------

Tasks can do more than just log simple messages.
They can... touch files as well.

.. code:: toml

   [[locations]]
   myfile = {file="blah.touched"}

   [[tasks.basic]]
   name = "file.toucher"
   actions = [
      {do="touch", args=["{myfile!p}"] },
   ]

---------------
Where To Go Now
---------------

Run ``doot list -actions`` to see a list of everything available
for ``{do="ACTION"}``. You can find the action's arguments with ``doot stub -actions ACTION``.
Or take a look at the :ref:`examples`.


