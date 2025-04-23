{# module.rst -*- mode: Jinja2 -*- #}
{% import "python/debug_obj.rst.jinja" as jgdb %}

.. _{{obj.name}}:

{% if obj.display %}
{% if is_own_page %}
{{ obj.id }}
{{ "=" * obj.id|length }}

.. py:module:: {{ obj.name }}

{% if obj.docstring %}
.. autoapi-nested-parse::

   {{ obj.docstring|indent(3) }}

{% endif %}

      {% block submodules %}
         {% set visible_subpackages = obj.subpackages|selectattr("display")|list %}
         {% set visible_submodules = obj.submodules|selectattr("display")|list %}
         {% set visible_submodules = (visible_subpackages + visible_submodules)|sort %}
         {% if visible_submodules %}
Submodules
----------

.. toctree::
   :maxdepth: 1

            {% for submodule in visible_submodules %}
   {{ submodule.include_path }}
            {% endfor %}


         {% endif %}
      {% endblock %}
      {% block content %}
         {% set visible_children = obj.children|selectattr("display")|list %}
         {% if visible_children %}
            {% set visible_data    = visible_children|selectattr("type", "equalto", "data")|list %}
            {% set visible_classes = visible_children|selectattr("type", "equalto", "class")|list %}

            {% include "python/vis_types.rst.jinja"   %}
            {% include "python/vis_enums.rst.jinja"   %}
            {% include "python/vis_protos.rst.jinja"  %}
            {% include "python/vis_attrs.rst.jinja"   %}
            {% include "python/vis_excs.rst.jinja"    %}
            {% include "python/vis_funcs.rst.jinja"   %}
            {% include "python/vis_classes.rst.jinja" %}

            {% set this_page_children = visible_children|rejectattr("type", "in", own_page_types)|list %}
            {% if this_page_children %}
{{ obj.type|title }} Contents
{{ "-" * obj.type|length }}---------

               {% for obj_item in this_page_children %}
{{ obj_item.render()|indent(0) }}
               {% endfor %}
            {% endif %}
         {% endif %}
      {% endblock %}
   {% else %}
.. py:module:: {{ obj.name }}

      {% if obj.docstring %}
   .. autoapi-nested-parse::

      {{ obj.docstring|indent(6) }}

      {% endif %}
      {% for obj_item in visible_children %}
   {{ obj_item.render()|indent(3) }}
      {% endfor %}
   {% endif %}
{% endif %}
