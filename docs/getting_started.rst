.. -*- mode: ReST -*-

================
Getting Started
================

.. contents:: Contents


------------
Installation
------------
.. code-block:: bash
   :linenos:

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


.. testcode:: bash

   doot

.. testoutput:: toml


---------------
Your First Task
---------------

.. testcode:: bash

   doot stub basic::task

.. testoutput:: toml


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

Adding CLI Params
-----------------

----------------------
Chaining a Second Task
----------------------

Passing Information between the Tasks
-------------------------------------

Cleaning Up
-----------

----------------------------
Handling Files And Locations
----------------------------
