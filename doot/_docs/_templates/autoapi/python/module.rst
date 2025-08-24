{# module.rst -*- mode: Jinja2 -*- #}
{% import "util/debug_obj.rst.jinja" as jgdb %}
{% import "util/headings.jinja" as utils %}

{% if obj.display %}
   {% set visible_children   = obj.children|selectattr("display")|list %}
   {% set mod_ns = namespace(children=[]) %}

   {{- utils.smartref(obj) }}

   
   {{- utils.heading(obj.id, above=True) }}

.. py:module:: {{ obj.name }}

   {% if obj.docstring -%}
.. autoapi-nested-parse::

   {{ obj.docstring|indent(3)}}
   {% endif %} 

   {# SUBMODULES #}
   {% block submodules -%}
   {%+ include "visible/vis_submods.rst.jinja" %}
   {% endblock submodules %}
   {# -------------------------------------------------- #}

   {% block summary -%}
      {% if visible_children %}
            {% set visible_data = visible_children|selectattr("type", "equalto", "data")|list %}
            {% set visible_classes = visible_children|selectattr("type", "equalto", "class")|list %}
            {% include "visible/vis_types.rst.jinja" %}
            {% include "visible/vis_enums.rst.jinja" %}
            {% include "visible/vis_protos.rst.jinja" %}
            {# {% include "visible/vis_attrs.rst.jinja" %}            #}
            {% include "visible/vis_excs.rst.jinja" %}
            {% include "visible/vis_funcs.rst.jinja" %}
            {% include "visible/vis_classes.rst.jinja" %}
      {% endif %}
   {% endblock summary %}

   {# -------------------------------------------------- #}
   {% if mod_ns.children %}
{{ obj.type|title }} Contents
{{ "=" * obj.type|length }}=========

      {% for obj_item in mod_ns.children %}
{{ obj_item.render()|indent(0) }}
      {% endfor %}
   {% endif %}

{% endif %}
