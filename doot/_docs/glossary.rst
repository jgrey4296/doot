.. -*- mode: ReST -*-

.. _glossary:

========
Glossary
========

.. contents::
   :local:

.. glossary::

   doot.toml
        The main config file.

   task.toml
        Files that provide :term:`taskspec`.

   taskspec
        A Toml Specification of a :term:`task`.

   action      
        The smallest unit of action, which can correspond to a function.
        
   task
        The Main unit of action, which structures :term:`action`'s with setup and cleanup actions.

   job
        A larger unit of action. A Task which can generate :term:`task`'s.
   
