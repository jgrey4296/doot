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


-----------------
Starting Concepts
-----------------

1. Files.

   The **doot.toml** file marks the root of a doot project. The **.tasks/{}.toml** files contain tasks. See :ref:`DootFileRef` and :ref:`TaskFileRef`.

2. Commands.

   Calling **doot** from the command line. See :ref:`runcmd`, :ref:`listcmd`, :ref:`stubcmd`.

3. Tasks and Actions.

   Specified in task toml files, these declaratively describe what you want to do. See :ref:`tasksRef`.

4. Names

   To refer to tasks, either from the command line, or from other tasks, they need a name. This takes the form of **group::name**. See :ref:`namesRef`.

-------------
The Doot File
-------------

When you initially run ``doot``, a stub ``doot.toml`` file will be created.
This allows you to customize plugins, locations, logging etc.

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

---------------
Your First Task
---------------

.. code:: bash

   doot stub basic::task


.. code:: toml

   [[tasks.basic]]
   name                 = "task"
   version              = "0.13.0"             # <str>                #
   doc                  = []                   # <list>               #
   ctor                 = "task"               # <str>                #
   depends_on           = []                   # <list[ActionSpec | RelationSpec]> #
   required_for         = []                   # <list[ActionSpec | RelationSpec]> #
   sources              = []                   # <list[TaskName | Path | NoneType]> #
   setup                = []                   # <list[ActionSpec | RelationSpec]> #
   cleanup              = []                   # <list[ActionSpec | RelationSpec]> #
   on_fail              = []                   # <list[ActionSpec | RelationSpec]> #
   priority             = 10                   # <int>                #
   queue_behaviour      = "default"            # <QueueMeta_e>        # reactive | onRegister | reactiveFail | default
   flags                = [ "TASK" ]           # <TaskMeta_f>         # STATELESS | TASK | REQ_TEARDOWN | DISABLED | THREAD_SAFE | IS_SETUP | EPHEMERAL | REQ_SETUP | IS_TEARDOWN | JOB_HEAD | INTERNAL | CONCRETE | STATEFUL | IDEMPOTENT | TRANSFORMER | JOB | VERSIONED
   inject               = []                   # <list>               #
   actions              = []                   # <list[ActionSpec | RelationSpec]> #

   Doot Shutting Down Normally



Action Groups
--------------

Tasks are specified in blocks of ``[[tasks.GROUPNAME]]``.

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

Tasks can pass information between each other using cli args.

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

Run ``doot plugins action`` to see a list of everything available
for ``{do="ACTION"}``. You can find the action's arguments with `doot stub -actions ACTION``.
