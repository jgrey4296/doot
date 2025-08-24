.. -*- mode: ReST -*-

.. _extending:

==============
Extending Doot
==============

.. contents:: Contents
   :local:


Aliquam erat volutpat.  Nunc eleifend leo vitae magna.  In id erat non orci
commodo lobortis.  Proin neque massa, cursus ut, gravida ut, lobortis eget,
lacus.  Sed diam.  Praesent fermentum tempor tellus.  Nullam tempus.  Mauris ac
felis vel velit tristique imperdiet.  Donec at pede.  Etiam vel neque nec dui
dignissim bibendum.  Vivamus id enim.  Phasellus neque orci, porta a, aliquet
quis, semper a, massa.  Phasellus purus.  Pellentesque tristique imperdiet
tortor.  Nam euismod tellus id erat.



Local Code
----------

The simplest way to add to doot is with simple local python functions.

.. code:: python


    def my_custom_function(spec,state) -> dict:
        return { "my_state_value": state['val'] + 1 }
    
          

Plugins
-------
          
Doot recognizes pyproject.toml ``entry-points``.
